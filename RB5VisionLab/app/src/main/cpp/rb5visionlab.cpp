#include <jni.h>
#include <string>
#include <dlfcn.h>
#include <vector>
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
