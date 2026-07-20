#include <jni.h>
#include <string>
#include <dlfcn.h>
#include <vector>
#include <algorithm>
#include <cstdint>
#include <android/log.h>
#include <opencv2/core.hpp>

#define LOG_TAG "RB5_NATIVE"
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)

namespace {

std::string checkLibrary(const char* library_name, const char* required_symbol) {
    dlerror();
    void* handle = dlopen(library_name, RTLD_NOW | RTLD_LOCAL);
    const char* open_error = dlerror();
    if (handle == nullptr) {
        std::string result = std::string(library_name) + ": dlopen failed";
        if (open_error != nullptr) {
            result += " (";
            result += open_error;
            result += ")";
        }
        return result;
    }

    std::string result = std::string(library_name) + ": loaded";
    if (required_symbol != nullptr) {
        dlerror();
        void* symbol = dlsym(handle, required_symbol);
        const char* symbol_error = dlerror();
        if (symbol == nullptr) {
            result += ", missing ";
            result += required_symbol;
            if (symbol_error != nullptr) {
                result += " (";
                result += symbol_error;
                result += ")";
            }
        } else {
            result += ", found ";
            result += required_symbol;
        }
    }
    dlclose(handle);
    return result;
}

using QnnDelegateAllocCustomMemFn = void* (*)(size_t, size_t);
using QnnDelegateFreeCustomMemFn = void (*)(void*);

std::string qnnDelegateSharedMemoryProbe(size_t input_bytes, size_t output_bytes) {
    constexpr size_t kTfLiteDefaultTensorAlignment = 64;
    dlerror();
    void* handle = dlopen("libQnnTFLiteDelegate.so", RTLD_NOW | RTLD_LOCAL);
    const char* open_error = dlerror();
    if (handle == nullptr) {
        std::string result = "status=blocked stage=dlopen library=libQnnTFLiteDelegate.so";
        if (open_error != nullptr) {
            result += " error=";
            result += open_error;
        }
        return result;
    }

    auto alloc_fn = reinterpret_cast<QnnDelegateAllocCustomMemFn>(
            dlsym(handle, "TfLiteQnnDelegateAllocCustomMem"));
    const char* alloc_error = dlerror();
    auto free_fn = reinterpret_cast<QnnDelegateFreeCustomMemFn>(
            dlsym(handle, "TfLiteQnnDelegateFreeCustomMem"));
    const char* free_error = dlerror();
    if (alloc_fn == nullptr || free_fn == nullptr) {
        std::string result = "status=blocked stage=dlsym";
        if (alloc_error != nullptr) {
            result += " alloc_error=";
            result += alloc_error;
        }
        if (free_error != nullptr) {
            result += " free_error=";
            result += free_error;
        }
        dlclose(handle);
        return result;
    }

    void* input_ptr = alloc_fn(input_bytes, kTfLiteDefaultTensorAlignment);
    void* output_ptr = alloc_fn(output_bytes, kTfLiteDefaultTensorAlignment);
    const bool input_aligned =
            reinterpret_cast<uintptr_t>(input_ptr) % kTfLiteDefaultTensorAlignment == 0;
    const bool output_aligned =
            reinterpret_cast<uintptr_t>(output_ptr) % kTfLiteDefaultTensorAlignment == 0;
    if (input_ptr != nullptr) {
        free_fn(input_ptr);
    }
    if (output_ptr != nullptr) {
        free_fn(output_ptr);
    }
    dlclose(handle);

    char result[512];
    snprintf(result, sizeof(result),
             "status=%s stage=alloc_free inputBytes=%zu outputBytes=%zu inputPtr=%s outputPtr=%s "
             "inputAligned=%s outputAligned=%s alignment=%zu",
             (input_ptr != nullptr && output_ptr != nullptr && input_aligned && output_aligned)
                     ? "pass" : "blocked",
             input_bytes,
             output_bytes,
             input_ptr != nullptr ? "non_null" : "null",
             output_ptr != nullptr ? "non_null" : "null",
             input_aligned ? "true" : "false",
             output_aligned ? "true" : "false",
             kTfLiteDefaultTensorAlignment);
    return result;
}

int clampToByte(float value) {
    return std::max(0, std::min(255, static_cast<int>(value)));
}

int yuvToArgb(int y, int u, int v) {
    const float yf = static_cast<float>(y);
    const float uf = static_cast<float>(u) - 128.0f;
    const float vf = static_cast<float>(v) - 128.0f;
    const int r = clampToByte(yf + 1.402f * vf);
    const int g = clampToByte(yf - 0.344136f * uf - 0.714136f * vf);
    const int b = clampToByte(yf + 1.772f * uf);
    return static_cast<int>(0xFF000000u | (static_cast<unsigned int>(r) << 16)
            | (static_cast<unsigned int>(g) << 8) | static_cast<unsigned int>(b));
}

}  // namespace

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_stringFromJNI(JNIEnv* env, jobject /* thiz */) {
    LOGD("Hello from C++ rb5visionlab.cpp");

    std::string message = "Hello from C++ on RB5 Gen2";
    return env->NewStringUTF(message.c_str());
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_qnnRuntimePreflight(JNIEnv* env, jobject /* thiz */) {
    const std::vector<std::string> checks = {
        checkLibrary("libQnnSystem.so", "QnnSystemInterface_getProviders"),
        checkLibrary("libQnnHtp.so", "QnnInterface_getProviders"),
        checkLibrary("libQnnHtpV73Stub.so", nullptr),
        checkLibrary("libQnnHtpPrepare.so", nullptr),
    };

    bool all_loaded = true;
    std::string message = "QNN preflight";
    for (const std::string& check : checks) {
        LOGD("%s", check.c_str());
        if (check.find("failed") != std::string::npos || check.find("missing") != std::string::npos) {
            all_loaded = false;
        }
        message += "\n";
        message += check;
    }
    message = std::string(all_loaded ? "QNN preflight OK" : "QNN preflight blocked") + message.substr(13);
    LOGD("%s", message.c_str());
    return env->NewStringUTF(message.c_str());
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_qnnSharedMemoryProbe(
        JNIEnv* env,
        jobject /* thiz */,
        jint input_bytes,
        jint output_bytes) {
    if (input_bytes <= 0 || output_bytes <= 0) {
        return env->NewStringUTF("status=blocked stage=argument error=non_positive_tensor_bytes");
    }
    const std::string result = qnnDelegateSharedMemoryProbe(
            static_cast<size_t>(input_bytes),
            static_cast<size_t>(output_bytes));
    LOGD("qnnSharedMemoryProbe %s", result.c_str());
    return env->NewStringUTF(result.c_str());
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_processYPlane(
        JNIEnv* env,
        jobject /* thiz */,
        jbyteArray y_data,
        jint width,
        jint height,
        jint row_stride) {
    if (y_data == nullptr || width <= 0 || height <= 0 || row_stride < width) {
        return env->NewStringUTF("native error: invalid Y plane");
    }

    jbyte* y_bytes = env->GetByteArrayElements(y_data, nullptr);
    if (y_bytes == nullptr) {
        return env->NewStringUTF("native error: cannot read Y plane");
    }

    cv::Mat y_mat(height, width, CV_8UC1, reinterpret_cast<unsigned char*>(y_bytes), row_stride);
    const double mean_y = cv::mean(y_mat)[0];

    env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);

    char result[128];
    snprintf(result, sizeof(result), "native OpenCV meanY=%.2f", mean_y);
    LOGD("%s width=%d height=%d rowStride=%d", result, width, height, row_stride);
    return env->NewStringUTF(result);
}

extern "C"
JNIEXPORT jintArray JNICALL
Java_com_cyf_rb5visionlab_MainActivity_nativeYuvToRgbRoi(
        JNIEnv* env,
        jobject /* thiz */,
        jbyteArray y_data,
        jbyteArray u_data,
        jbyteArray v_data,
        jint width,
        jint height,
        jint y_row_stride,
        jint y_pixel_stride,
        jint u_row_stride,
        jint u_pixel_stride,
        jint v_row_stride,
        jint v_pixel_stride,
        jint output_side) {
    if (y_data == nullptr || u_data == nullptr || v_data == nullptr ||
        width <= 0 || height <= 0 || output_side <= 0 ||
        y_row_stride <= 0 || u_row_stride <= 0 || v_row_stride <= 0 ||
        y_pixel_stride <= 0 || u_pixel_stride <= 0 || v_pixel_stride <= 0) {
        return nullptr;
    }

    jbyte* y_bytes = env->GetByteArrayElements(y_data, nullptr);
    jbyte* u_bytes = env->GetByteArrayElements(u_data, nullptr);
    jbyte* v_bytes = env->GetByteArrayElements(v_data, nullptr);
    if (y_bytes == nullptr || u_bytes == nullptr || v_bytes == nullptr) {
        if (y_bytes != nullptr) env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);
        if (u_bytes != nullptr) env->ReleaseByteArrayElements(u_data, u_bytes, JNI_ABORT);
        if (v_bytes != nullptr) env->ReleaseByteArrayElements(v_data, v_bytes, JNI_ABORT);
        return nullptr;
    }

    const int crop_side = std::max(
            output_side,
            std::min({width * output_side / 640, width, height}));
    const int left = (width - crop_side) / 2;
    const int top = (height - crop_side) / 2;
    const int pixel_count = output_side * output_side;
    jintArray result = env->NewIntArray(pixel_count);
    if (result == nullptr) {
        env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);
        env->ReleaseByteArrayElements(u_data, u_bytes, JNI_ABORT);
        env->ReleaseByteArrayElements(v_data, v_bytes, JNI_ABORT);
        return nullptr;
    }

    std::vector<jint> pixels(pixel_count);
    for (int oy = 0; oy < output_side; ++oy) {
        const int src_y = top + (oy * crop_side + crop_side / (output_side * 2)) / output_side;
        const int y_base = src_y * y_row_stride;
        const int uv_y = src_y / 2;
        const int u_base = uv_y * u_row_stride;
        const int v_base = uv_y * v_row_stride;
        for (int ox = 0; ox < output_side; ++ox) {
            const int src_x = left + (ox * crop_side + crop_side / (output_side * 2)) / output_side;
            const int uv_x = src_x / 2;
            const int y_value = static_cast<unsigned char>(y_bytes[y_base + src_x * y_pixel_stride]);
            const int u_value = static_cast<unsigned char>(u_bytes[u_base + uv_x * u_pixel_stride]);
            const int v_value = static_cast<unsigned char>(v_bytes[v_base + uv_x * v_pixel_stride]);
            pixels[oy * output_side + ox] = yuvToArgb(y_value, u_value, v_value);
        }
    }

    env->SetIntArrayRegion(result, 0, pixel_count, pixels.data());
    env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);
    env->ReleaseByteArrayElements(u_data, u_bytes, JNI_ABORT);
    env->ReleaseByteArrayElements(v_data, v_bytes, JNI_ABORT);
    LOGD("nativeYuvToRgbRoi width=%d height=%d crop=%d output=%d yRow=%d uRow=%d vRow=%d uPixel=%d vPixel=%d",
         width, height, crop_side, output_side, y_row_stride, u_row_stride, v_row_stride,
         u_pixel_stride, v_pixel_stride);
    return result;
}

extern "C"
JNIEXPORT jbyteArray JNICALL
Java_com_cyf_rb5visionlab_MainActivity_nativeYuvToRgbRoiBytes(
        JNIEnv* env,
        jobject /* thiz */,
        jbyteArray y_data,
        jbyteArray u_data,
        jbyteArray v_data,
        jint width,
        jint height,
        jint y_row_stride,
        jint y_pixel_stride,
        jint u_row_stride,
        jint u_pixel_stride,
        jint v_row_stride,
        jint v_pixel_stride,
        jint output_side) {
    if (y_data == nullptr || u_data == nullptr || v_data == nullptr ||
        width <= 0 || height <= 0 || output_side <= 0 ||
        y_row_stride <= 0 || u_row_stride <= 0 || v_row_stride <= 0 ||
        y_pixel_stride <= 0 || u_pixel_stride <= 0 || v_pixel_stride <= 0) {
        return nullptr;
    }

    jbyte* y_bytes = env->GetByteArrayElements(y_data, nullptr);
    jbyte* u_bytes = env->GetByteArrayElements(u_data, nullptr);
    jbyte* v_bytes = env->GetByteArrayElements(v_data, nullptr);
    if (y_bytes == nullptr || u_bytes == nullptr || v_bytes == nullptr) {
        if (y_bytes != nullptr) env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);
        if (u_bytes != nullptr) env->ReleaseByteArrayElements(u_data, u_bytes, JNI_ABORT);
        if (v_bytes != nullptr) env->ReleaseByteArrayElements(v_data, v_bytes, JNI_ABORT);
        return nullptr;
    }

    const int crop_side = std::max(
            output_side,
            std::min({width * output_side / 640, width, height}));
    const int left = (width - crop_side) / 2;
    const int top = (height - crop_side) / 2;
    const int byte_count = output_side * output_side * 3;
    jbyteArray result = env->NewByteArray(byte_count);
    if (result == nullptr) {
        env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);
        env->ReleaseByteArrayElements(u_data, u_bytes, JNI_ABORT);
        env->ReleaseByteArrayElements(v_data, v_bytes, JNI_ABORT);
        return nullptr;
    }

    std::vector<jbyte> rgb(byte_count);
    for (int oy = 0; oy < output_side; ++oy) {
        const int src_y = top + (oy * crop_side + crop_side / (output_side * 2)) / output_side;
        const int y_base = src_y * y_row_stride;
        const int uv_y = src_y / 2;
        const int u_base = uv_y * u_row_stride;
        const int v_base = uv_y * v_row_stride;
        for (int ox = 0; ox < output_side; ++ox) {
            const int src_x = left + (ox * crop_side + crop_side / (output_side * 2)) / output_side;
            const int uv_x = src_x / 2;
            const int y_value = static_cast<unsigned char>(y_bytes[y_base + src_x * y_pixel_stride]);
            const int u_value = static_cast<unsigned char>(u_bytes[u_base + uv_x * u_pixel_stride]);
            const int v_value = static_cast<unsigned char>(v_bytes[v_base + uv_x * v_pixel_stride]);
            const float yf = static_cast<float>(y_value);
            const float uf = static_cast<float>(u_value) - 128.0f;
            const float vf = static_cast<float>(v_value) - 128.0f;
            const int out = (oy * output_side + ox) * 3;
            rgb[out] = static_cast<jbyte>(clampToByte(yf + 1.402f * vf));
            rgb[out + 1] = static_cast<jbyte>(clampToByte(yf - 0.344136f * uf - 0.714136f * vf));
            rgb[out + 2] = static_cast<jbyte>(clampToByte(yf + 1.772f * uf));
        }
    }

    env->SetByteArrayRegion(result, 0, byte_count, rgb.data());
    env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);
    env->ReleaseByteArrayElements(u_data, u_bytes, JNI_ABORT);
    env->ReleaseByteArrayElements(v_data, v_bytes, JNI_ABORT);
    LOGD("nativeYuvToRgbRoiBytes width=%d height=%d crop=%d output=%d", width, height, crop_side, output_side);
    return result;
}
