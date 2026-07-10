#include <jni.h>
#include <string>
#include <android/log.h>
#include <opencv2/core.hpp>

#define LOG_TAG "RB5_NATIVE"
#define LOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_stringFromJNI(JNIEnv* env, jobject /* thiz */) {
    LOGD("Hello from C++ rb5visionlab.cpp");

    std::string message = "Hello from C++ on RB5 Gen2";
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
