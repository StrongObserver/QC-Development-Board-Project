#include <jni.h>
#include <string>
#include <dlfcn.h>
#include <vector>
#include <algorithm>
#include <cstdint>
#include <numeric>
#include <chrono>
#include <android/log.h>
#include <android/asset_manager.h>
#include <android/asset_manager_jni.h>
#include <android/hardware_buffer.h>
#include <android/hardware_buffer_jni.h>
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

struct DynamicLibrary {
    explicit DynamicLibrary(const char* name) : handle(dlopen(name, RTLD_NOW | RTLD_LOCAL)) {}
    ~DynamicLibrary() {
        if (handle != nullptr) {
            dlclose(handle);
        }
    }
    DynamicLibrary(const DynamicLibrary&) = delete;
    DynamicLibrary& operator=(const DynamicLibrary&) = delete;
    void* handle = nullptr;
};

template <typename Fn>
Fn loadSymbol(void* handle, const char* name) {
    dlerror();
    void* symbol = dlsym(handle, name);
    return reinterpret_cast<Fn>(symbol);
}

struct TfLiteModel;
struct TfLiteInterpreterOptions;
struct TfLiteInterpreter;
struct TfLiteTensor;
using TfLiteOpaqueDelegate = void;
using TfLiteStatus = int;

struct TfLiteCustomAllocationNative {
    void* data;
    size_t bytes;
};

void yuvToRgb(int y, int u, int v, jbyte* out);
int normalizeRotation(int rotation_degrees);
int rotatedOutputIndex(int x, int y, int side, int rotation_degrees);

using TfLiteModelCreateFn = TfLiteModel* (*)(const void*, size_t);
using TfLiteModelDeleteFn = void (*)(TfLiteModel*);
using TfLiteInterpreterOptionsCreateFn = TfLiteInterpreterOptions* (*)();
using TfLiteInterpreterOptionsDeleteFn = void (*)(TfLiteInterpreterOptions*);
using TfLiteInterpreterOptionsSetNumThreadsFn = void (*)(TfLiteInterpreterOptions*, int32_t);
using TfLiteInterpreterCreateFn = TfLiteInterpreter* (*)(const TfLiteModel*, const TfLiteInterpreterOptions*);
using TfLiteInterpreterDeleteFn = void (*)(TfLiteInterpreter*);
using TfLiteInterpreterGetInputTensorIndexFn = int32_t (*)(const TfLiteInterpreter*, int32_t);
using TfLiteInterpreterGetOutputTensorIndexFn = int32_t (*)(const TfLiteInterpreter*, int32_t);
using TfLiteInterpreterSetCustomAllocationForTensorFn =
        TfLiteStatus (*)(TfLiteInterpreter*, int, const TfLiteCustomAllocationNative*, int64_t);
using TfLiteInterpreterAllocateTensorsFn = TfLiteStatus (*)(TfLiteInterpreter*);
using TfLiteInterpreterModifyGraphWithDelegateFn =
        TfLiteStatus (*)(TfLiteInterpreter*, TfLiteOpaqueDelegate*);
using TfLiteInterpreterInvokeFn = TfLiteStatus (*)(TfLiteInterpreter*);
using TfLiteInterpreterGetInputTensorFn = TfLiteTensor* (*)(const TfLiteInterpreter*, int32_t);
using TfLiteInterpreterGetOutputTensorFn = const TfLiteTensor* (*)(const TfLiteInterpreter*, int32_t);
using TfLiteTensorDataFn = void* (*)(const TfLiteTensor*);
using TfLiteTensorByteSizeFn = size_t (*)(const TfLiteTensor*);

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

bool readAssetBytes(JNIEnv* env, jobject asset_manager, const char* asset_name, std::vector<uint8_t>& bytes) {
    AAssetManager* manager = AAssetManager_fromJava(env, asset_manager);
    if (manager == nullptr) {
        return false;
    }
    AAsset* asset = AAssetManager_open(manager, asset_name, AASSET_MODE_BUFFER);
    if (asset == nullptr) {
        return false;
    }
    const off64_t length = AAsset_getLength64(asset);
    if (length <= 0) {
        AAsset_close(asset);
        return false;
    }
    bytes.resize(static_cast<size_t>(length));
    const int64_t read = AAsset_read(asset, bytes.data(), bytes.size());
    AAsset_close(asset);
    return read == static_cast<int64_t>(bytes.size());
}

struct TfLiteApi {
    TfLiteModelCreateFn modelCreate = nullptr;
    TfLiteModelDeleteFn modelDelete = nullptr;
    TfLiteInterpreterOptionsCreateFn optionsCreate = nullptr;
    TfLiteInterpreterOptionsDeleteFn optionsDelete = nullptr;
    TfLiteInterpreterOptionsSetNumThreadsFn optionsSetThreads = nullptr;
    TfLiteInterpreterCreateFn interpreterCreate = nullptr;
    TfLiteInterpreterDeleteFn interpreterDelete = nullptr;
    TfLiteInterpreterGetInputTensorIndexFn inputIndex = nullptr;
    TfLiteInterpreterGetOutputTensorIndexFn outputIndex = nullptr;
    TfLiteInterpreterSetCustomAllocationForTensorFn setCustomAllocation = nullptr;
    TfLiteInterpreterAllocateTensorsFn allocateTensors = nullptr;
    TfLiteInterpreterModifyGraphWithDelegateFn modifyGraph = nullptr;
    TfLiteInterpreterInvokeFn invoke = nullptr;
    TfLiteInterpreterGetInputTensorFn getInputTensor = nullptr;
    TfLiteInterpreterGetOutputTensorFn getOutputTensor = nullptr;
    TfLiteTensorDataFn tensorData = nullptr;
    TfLiteTensorByteSizeFn tensorByteSize = nullptr;
};

TfLiteApi loadTfLiteApi(void* handle) {
    TfLiteApi api;
    api.modelCreate = loadSymbol<TfLiteModelCreateFn>(handle, "TfLiteModelCreate");
    api.modelDelete = loadSymbol<TfLiteModelDeleteFn>(handle, "TfLiteModelDelete");
    api.optionsCreate = loadSymbol<TfLiteInterpreterOptionsCreateFn>(handle, "TfLiteInterpreterOptionsCreate");
    api.optionsDelete = loadSymbol<TfLiteInterpreterOptionsDeleteFn>(handle, "TfLiteInterpreterOptionsDelete");
    api.optionsSetThreads = loadSymbol<TfLiteInterpreterOptionsSetNumThreadsFn>(
            handle, "TfLiteInterpreterOptionsSetNumThreads");
    api.interpreterCreate = loadSymbol<TfLiteInterpreterCreateFn>(handle, "TfLiteInterpreterCreate");
    api.interpreterDelete = loadSymbol<TfLiteInterpreterDeleteFn>(handle, "TfLiteInterpreterDelete");
    api.inputIndex = loadSymbol<TfLiteInterpreterGetInputTensorIndexFn>(
            handle, "TfLiteInterpreterGetInputTensorIndex");
    api.outputIndex = loadSymbol<TfLiteInterpreterGetOutputTensorIndexFn>(
            handle, "TfLiteInterpreterGetOutputTensorIndex");
    api.setCustomAllocation = loadSymbol<TfLiteInterpreterSetCustomAllocationForTensorFn>(
            handle, "TfLiteInterpreterSetCustomAllocationForTensor");
    api.allocateTensors = loadSymbol<TfLiteInterpreterAllocateTensorsFn>(
            handle, "TfLiteInterpreterAllocateTensors");
    api.modifyGraph = loadSymbol<TfLiteInterpreterModifyGraphWithDelegateFn>(
            handle, "TfLiteInterpreterModifyGraphWithDelegate");
    api.invoke = loadSymbol<TfLiteInterpreterInvokeFn>(handle, "TfLiteInterpreterInvoke");
    api.getInputTensor = loadSymbol<TfLiteInterpreterGetInputTensorFn>(
            handle, "TfLiteInterpreterGetInputTensor");
    api.getOutputTensor = loadSymbol<TfLiteInterpreterGetOutputTensorFn>(
            handle, "TfLiteInterpreterGetOutputTensor");
    api.tensorData = loadSymbol<TfLiteTensorDataFn>(handle, "TfLiteTensorData");
    api.tensorByteSize = loadSymbol<TfLiteTensorByteSizeFn>(handle, "TfLiteTensorByteSize");
    return api;
}

bool hasRequiredTfLiteApi(const TfLiteApi& api, bool needs_custom_allocation) {
    return api.modelCreate != nullptr && api.modelDelete != nullptr &&
           api.optionsCreate != nullptr && api.optionsDelete != nullptr &&
           api.optionsSetThreads != nullptr && api.interpreterCreate != nullptr &&
           api.interpreterDelete != nullptr && api.inputIndex != nullptr &&
           api.outputIndex != nullptr && api.allocateTensors != nullptr &&
           api.modifyGraph != nullptr && api.invoke != nullptr &&
           api.getInputTensor != nullptr && api.getOutputTensor != nullptr &&
           api.tensorData != nullptr && api.tensorByteSize != nullptr &&
           (!needs_custom_allocation || api.setCustomAllocation != nullptr);
}

void fillSyntheticInput(uint8_t* input_bytes, size_t input_size) {
    if (input_bytes == nullptr) {
        return;
    }
    for (size_t i = 0; i < input_size; ++i) {
        input_bytes[i] = static_cast<uint8_t>((i * 17 + 31) & 0xFF);
    }
}

struct OutputSample {
    uint32_t checksum = 0;
    uint8_t minValue = 255;
    uint8_t maxValue = 0;
};

OutputSample sampleOutputBytes(const uint8_t* output_bytes, size_t output_size) {
    OutputSample sample;
    if (output_bytes == nullptr || output_size == 0) {
        sample.minValue = 0;
        return sample;
    }
    for (size_t i = 0; i < output_size; i += 4096) {
        const uint8_t value = output_bytes[i];
        sample.checksum = sample.checksum * 131u + value;
        sample.minValue = std::min(sample.minValue, value);
        sample.maxValue = std::max(sample.maxValue, value);
    }
    return sample;
}

int64_t averageMicros(const std::vector<int64_t>& values) {
    return values.empty()
            ? -1
            : std::accumulate(values.begin(), values.end(), int64_t{0}) /
                    static_cast<int64_t>(values.size());
}

int64_t minMicros(const std::vector<int64_t>& values) {
    return values.empty() ? -1 : *std::min_element(values.begin(), values.end());
}

int64_t maxMicros(const std::vector<int64_t>& values) {
    return values.empty() ? -1 : *std::max_element(values.begin(), values.end());
}

std::string qnnDelegateSharedTensorProbe(
        JNIEnv* env,
        jobject asset_manager,
        const char* model_asset,
        intptr_t delegate_handle,
        int repeats) {
    constexpr size_t kTfLiteDefaultTensorAlignment = 64;
    constexpr size_t kInputBytes = 128 * 128 * 3;
    constexpr size_t kOutputBytes = 512 * 512 * 3;
    if (delegate_handle == 0) {
        return "status=blocked stage=argument error=null_delegate_handle";
    }

    std::vector<uint8_t> model_bytes;
    if (!readAssetBytes(env, asset_manager, model_asset, model_bytes)) {
        return "status=blocked stage=asset error=read_model_failed";
    }

    DynamicLibrary tflite("libtensorflowlite_jni.so");
    if (tflite.handle == nullptr) {
        return "status=blocked stage=dlopen library=libtensorflowlite_jni.so";
    }
    DynamicLibrary qnn("libQnnTFLiteDelegate.so");
    if (qnn.handle == nullptr) {
        return "status=blocked stage=dlopen library=libQnnTFLiteDelegate.so";
    }

    const TfLiteApi api = loadTfLiteApi(tflite.handle);
    auto alloc_mem = loadSymbol<QnnDelegateAllocCustomMemFn>(qnn.handle, "TfLiteQnnDelegateAllocCustomMem");
    auto free_mem = loadSymbol<QnnDelegateFreeCustomMemFn>(qnn.handle, "TfLiteQnnDelegateFreeCustomMem");

    if (!hasRequiredTfLiteApi(api, true) || alloc_mem == nullptr || free_mem == nullptr) {
        return "status=blocked stage=dlsym error=missing_tflite_or_qnn_symbol";
    }

    TfLiteModel* model = api.modelCreate(model_bytes.data(), model_bytes.size());
    if (model == nullptr) {
        return "status=blocked stage=model_create";
    }
    TfLiteInterpreterOptions* options = api.optionsCreate();
    if (options == nullptr) {
        api.modelDelete(model);
        return "status=blocked stage=options_create";
    }
    api.optionsSetThreads(options, 1);
    TfLiteInterpreter* interpreter = api.interpreterCreate(model, options);
    api.optionsDelete(options);
    if (interpreter == nullptr) {
        api.modelDelete(model);
        return "status=blocked stage=interpreter_create";
    }

    const int input_tensor_index = api.inputIndex(interpreter, 0);
    const int output_tensor_index = api.outputIndex(interpreter, 0);
    void* input_ptr = alloc_mem(kInputBytes, kTfLiteDefaultTensorAlignment);
    void* output_ptr = alloc_mem(kOutputBytes, kTfLiteDefaultTensorAlignment);
    if (input_ptr == nullptr || output_ptr == nullptr || input_tensor_index < 0 || output_tensor_index < 0) {
        if (input_ptr != nullptr) free_mem(input_ptr);
        if (output_ptr != nullptr) free_mem(output_ptr);
        api.interpreterDelete(interpreter);
        api.modelDelete(model);
        return "status=blocked stage=prepare_custom_allocation";
    }

    TfLiteCustomAllocationNative input_alloc{input_ptr, kInputBytes};
    TfLiteCustomAllocationNative output_alloc{output_ptr, kOutputBytes};
    const TfLiteStatus input_alloc_status =
            api.setCustomAllocation(interpreter, input_tensor_index, &input_alloc, 0);
    const TfLiteStatus output_alloc_status =
            api.setCustomAllocation(interpreter, output_tensor_index, &output_alloc, 0);
    const TfLiteStatus allocate_status = api.allocateTensors(interpreter);
    TfLiteTensor* input_tensor = api.getInputTensor(interpreter, 0);
    const TfLiteTensor* output_tensor = api.getOutputTensor(interpreter, 0);
    const bool input_bound = input_tensor != nullptr && api.tensorData(input_tensor) == input_ptr;
    const bool output_bound = output_tensor != nullptr && api.tensorData(output_tensor) == output_ptr;
    const size_t input_tensor_bytes = input_tensor != nullptr ? api.tensorByteSize(input_tensor) : 0;
    const size_t output_tensor_bytes = output_tensor != nullptr ? api.tensorByteSize(output_tensor) : 0;
    const auto delegate_start = std::chrono::steady_clock::now();
    const TfLiteStatus delegate_status =
            api.modifyGraph(interpreter, reinterpret_cast<TfLiteOpaqueDelegate*>(delegate_handle));
    const auto delegate_end = std::chrono::steady_clock::now();

    uint8_t* input_bytes = reinterpret_cast<uint8_t*>(input_ptr);
    fillSyntheticInput(input_bytes, kInputBytes);
    int invoke_status = delegate_status;
    std::vector<int64_t> invoke_times_us;
    if (delegate_status == 0) {
        for (int i = 0; i < repeats; ++i) {
            const auto invoke_start = std::chrono::steady_clock::now();
            invoke_status = api.invoke(interpreter);
            const auto invoke_end = std::chrono::steady_clock::now();
            invoke_times_us.push_back(std::chrono::duration_cast<std::chrono::microseconds>(
                    invoke_end - invoke_start).count());
            if (invoke_status != 0) {
                break;
            }
        }
    }
    const uint8_t* output_bytes = reinterpret_cast<const uint8_t*>(output_ptr);
    const OutputSample output_sample = sampleOutputBytes(output_bytes, kOutputBytes);

    const bool passed = input_alloc_status == 0 && output_alloc_status == 0 &&
                        allocate_status == 0 && delegate_status == 0 && invoke_status == 0 &&
                        input_bound && output_bound &&
                        input_tensor_bytes <= kInputBytes && output_tensor_bytes <= kOutputBytes;
    const int64_t delegate_us = std::chrono::duration_cast<std::chrono::microseconds>(
            delegate_end - delegate_start).count();
    const int64_t invoke_min_us = minMicros(invoke_times_us);
    const int64_t invoke_max_us = maxMicros(invoke_times_us);
    const int64_t invoke_avg_us = averageMicros(invoke_times_us);

    api.interpreterDelete(interpreter);
    api.modelDelete(model);
    free_mem(input_ptr);
    free_mem(output_ptr);

    char result[768];
    snprintf(result, sizeof(result),
             "status=%s stage=tensor_bind_invoke modelBytes=%zu inputIndex=%d outputIndex=%d "
             "inputAlloc=%d outputAlloc=%d allocate=%d delegate=%d invoke=%d "
             "inputBound=%s outputBound=%s inputTensorBytes=%zu outputTensorBytes=%zu "
             "checksum=%u sampledMin=%u sampledMax=%u repeats=%d completedRuns=%zu "
             "delegateUs=%lld invokeAvgUs=%lld invokeMinUs=%lld invokeMaxUs=%lld",
             passed ? "pass" : "blocked",
             model_bytes.size(),
             input_tensor_index,
             output_tensor_index,
             input_alloc_status,
             output_alloc_status,
             allocate_status,
             delegate_status,
             invoke_status,
             input_bound ? "true" : "false",
             output_bound ? "true" : "false",
             input_tensor_bytes,
             output_tensor_bytes,
             output_sample.checksum,
             static_cast<unsigned int>(output_sample.minValue),
             static_cast<unsigned int>(output_sample.maxValue),
             repeats,
             invoke_times_us.size(),
             static_cast<long long>(delegate_us),
             static_cast<long long>(invoke_avg_us),
             static_cast<long long>(invoke_min_us),
             static_cast<long long>(invoke_max_us));
    return result;
}

struct TensorProbeRun {
    bool passed = false;
    std::string blockedStage;
    int inputIndex = -1;
    int outputIndex = -1;
    int inputAllocStatus = -1;
    int outputAllocStatus = -1;
    int allocateStatus = -1;
    int delegateStatus = -1;
    int invokeStatus = -1;
    bool inputBound = false;
    bool outputBound = false;
    size_t inputTensorBytes = 0;
    size_t outputTensorBytes = 0;
    OutputSample outputSample;
    size_t completedRuns = 0;
    int64_t inputFillUs = -1;
    int64_t delegateUs = -1;
    int64_t invokeAvgUs = -1;
    int64_t invokeMinUs = -1;
    int64_t invokeMaxUs = -1;
};

TensorProbeRun runTensorProbeVariant(
        const TfLiteApi& api,
        const std::vector<uint8_t>& model_bytes,
        intptr_t delegate_handle,
        bool use_custom_allocation,
        QnnDelegateAllocCustomMemFn alloc_mem,
        QnnDelegateFreeCustomMemFn free_mem,
        int repeats) {
    constexpr size_t kTfLiteDefaultTensorAlignment = 64;
    constexpr size_t kInputBytes = 128 * 128 * 3;
    constexpr size_t kOutputBytes = 512 * 512 * 3;
    TensorProbeRun result;
    void* custom_input_ptr = nullptr;
    void* custom_output_ptr = nullptr;

    TfLiteModel* model = api.modelCreate(model_bytes.data(), model_bytes.size());
    if (model == nullptr) {
        result.blockedStage = "model_create";
        return result;
    }
    TfLiteInterpreterOptions* options = api.optionsCreate();
    if (options == nullptr) {
        api.modelDelete(model);
        result.blockedStage = "options_create";
        return result;
    }
    api.optionsSetThreads(options, 1);
    TfLiteInterpreter* interpreter = api.interpreterCreate(model, options);
    api.optionsDelete(options);
    if (interpreter == nullptr) {
        api.modelDelete(model);
        result.blockedStage = "interpreter_create";
        return result;
    }

    result.inputIndex = api.inputIndex(interpreter, 0);
    result.outputIndex = api.outputIndex(interpreter, 0);
    if (result.inputIndex < 0 || result.outputIndex < 0) {
        result.blockedStage = "tensor_index";
        api.interpreterDelete(interpreter);
        api.modelDelete(model);
        return result;
    }

    if (use_custom_allocation) {
        custom_input_ptr = alloc_mem(kInputBytes, kTfLiteDefaultTensorAlignment);
        custom_output_ptr = alloc_mem(kOutputBytes, kTfLiteDefaultTensorAlignment);
        if (custom_input_ptr == nullptr || custom_output_ptr == nullptr) {
            result.blockedStage = "custom_alloc";
            if (custom_input_ptr != nullptr) free_mem(custom_input_ptr);
            if (custom_output_ptr != nullptr) free_mem(custom_output_ptr);
            api.interpreterDelete(interpreter);
            api.modelDelete(model);
            return result;
        }
        TfLiteCustomAllocationNative input_alloc{custom_input_ptr, kInputBytes};
        TfLiteCustomAllocationNative output_alloc{custom_output_ptr, kOutputBytes};
        result.inputAllocStatus =
                api.setCustomAllocation(interpreter, result.inputIndex, &input_alloc, 0);
        result.outputAllocStatus =
                api.setCustomAllocation(interpreter, result.outputIndex, &output_alloc, 0);
    } else {
        result.inputAllocStatus = 0;
        result.outputAllocStatus = 0;
    }

    result.allocateStatus = api.allocateTensors(interpreter);
    TfLiteTensor* input_tensor = api.getInputTensor(interpreter, 0);
    const TfLiteTensor* output_tensor = api.getOutputTensor(interpreter, 0);
    void* input_ptr = input_tensor != nullptr ? api.tensorData(input_tensor) : nullptr;
    const void* output_ptr = output_tensor != nullptr ? api.tensorData(output_tensor) : nullptr;
    result.inputTensorBytes = input_tensor != nullptr ? api.tensorByteSize(input_tensor) : 0;
    result.outputTensorBytes = output_tensor != nullptr ? api.tensorByteSize(output_tensor) : 0;
    result.inputBound = use_custom_allocation ? input_ptr == custom_input_ptr : input_ptr != nullptr;
    result.outputBound = use_custom_allocation ? output_ptr == custom_output_ptr : output_ptr != nullptr;

    const auto delegate_start = std::chrono::steady_clock::now();
    result.delegateStatus =
            api.modifyGraph(interpreter, reinterpret_cast<TfLiteOpaqueDelegate*>(delegate_handle));
    const auto delegate_end = std::chrono::steady_clock::now();
    result.delegateUs = std::chrono::duration_cast<std::chrono::microseconds>(
            delegate_end - delegate_start).count();

    input_tensor = api.getInputTensor(interpreter, 0);
    output_tensor = api.getOutputTensor(interpreter, 0);
    input_ptr = input_tensor != nullptr ? api.tensorData(input_tensor) : input_ptr;
    output_ptr = output_tensor != nullptr ? api.tensorData(output_tensor) : output_ptr;
    result.inputTensorBytes = input_tensor != nullptr ? api.tensorByteSize(input_tensor) : result.inputTensorBytes;
    result.outputTensorBytes = output_tensor != nullptr ? api.tensorByteSize(output_tensor) : result.outputTensorBytes;
    result.inputBound = use_custom_allocation ? input_ptr == custom_input_ptr : input_ptr != nullptr;
    result.outputBound = use_custom_allocation ? output_ptr == custom_output_ptr : output_ptr != nullptr;

    fillSyntheticInput(reinterpret_cast<uint8_t*>(input_ptr), std::min(result.inputTensorBytes, kInputBytes));
    std::vector<int64_t> invoke_times_us;
    result.invokeStatus = result.delegateStatus;
    if (result.delegateStatus == 0) {
        for (int i = 0; i < repeats; ++i) {
            const auto invoke_start = std::chrono::steady_clock::now();
            result.invokeStatus = api.invoke(interpreter);
            const auto invoke_end = std::chrono::steady_clock::now();
            invoke_times_us.push_back(std::chrono::duration_cast<std::chrono::microseconds>(
                    invoke_end - invoke_start).count());
            if (result.invokeStatus != 0) {
                break;
            }
        }
    }
    result.completedRuns = invoke_times_us.size();
    result.invokeAvgUs = averageMicros(invoke_times_us);
    result.invokeMinUs = minMicros(invoke_times_us);
    result.invokeMaxUs = maxMicros(invoke_times_us);
    result.outputSample = sampleOutputBytes(
            reinterpret_cast<const uint8_t*>(output_ptr),
            std::min(result.outputTensorBytes, kOutputBytes));
    result.passed = result.inputAllocStatus == 0 && result.outputAllocStatus == 0 &&
                    result.allocateStatus == 0 && result.delegateStatus == 0 &&
                    result.invokeStatus == 0 && result.inputBound && result.outputBound &&
                    result.inputTensorBytes <= kInputBytes &&
                    result.outputTensorBytes <= kOutputBytes;

    api.interpreterDelete(interpreter);
    api.modelDelete(model);
    if (custom_input_ptr != nullptr) free_mem(custom_input_ptr);
    if (custom_output_ptr != nullptr) free_mem(custom_output_ptr);
    return result;
}

bool fillDirectYuvRoiRgb(
        const uint8_t* y_bytes,
        const uint8_t* u_bytes,
        const uint8_t* v_bytes,
        int width,
        int height,
        int y_row_stride,
        int y_pixel_stride,
        int u_row_stride,
        int u_pixel_stride,
        int v_row_stride,
        int v_pixel_stride,
        int output_side,
        int rotation_degrees,
        uint8_t* output_rgb) {
    if (y_bytes == nullptr || u_bytes == nullptr || v_bytes == nullptr || output_rgb == nullptr ||
        width <= 0 || height <= 0 || output_side <= 0 ||
        y_row_stride <= 0 || u_row_stride <= 0 || v_row_stride <= 0 ||
        y_pixel_stride <= 0 || u_pixel_stride <= 0 || v_pixel_stride <= 0) {
        return false;
    }
    const int crop_side = std::max(
            output_side,
            std::min({width * output_side / 640, width, height}));
    const int left = (width - crop_side) / 2;
    const int top = (height - crop_side) / 2;
    auto* out = reinterpret_cast<jbyte*>(output_rgb);
    for (int oy = 0; oy < output_side; ++oy) {
        const int src_y = top + (oy * crop_side + crop_side / (output_side * 2)) / output_side;
        const int y_base = src_y * y_row_stride;
        const int uv_y = src_y / 2;
        const int u_base = uv_y * u_row_stride;
        const int v_base = uv_y * v_row_stride;
        for (int ox = 0; ox < output_side; ++ox) {
            const int src_x = left + (ox * crop_side + crop_side / (output_side * 2)) / output_side;
            const int uv_x = src_x / 2;
            const int y_value = y_bytes[y_base + src_x * y_pixel_stride];
            const int u_value = u_bytes[u_base + uv_x * u_pixel_stride];
            const int v_value = v_bytes[v_base + uv_x * v_pixel_stride];
            const int out_index = rotatedOutputIndex(ox, oy, output_side, rotation_degrees) * 3;
            yuvToRgb(y_value, u_value, v_value, out + out_index);
        }
    }
    return true;
}

TensorProbeRun runCameraTensorProbeVariant(
        const TfLiteApi& api,
        const std::vector<uint8_t>& model_bytes,
        intptr_t delegate_handle,
        bool use_custom_allocation,
        QnnDelegateAllocCustomMemFn alloc_mem,
        QnnDelegateFreeCustomMemFn free_mem,
        int repeats,
        const uint8_t* y_bytes,
        const uint8_t* u_bytes,
        const uint8_t* v_bytes,
        int width,
        int height,
        int y_row_stride,
        int y_pixel_stride,
        int u_row_stride,
        int u_pixel_stride,
        int v_row_stride,
        int v_pixel_stride,
        int output_side,
        int rotation_degrees) {
    constexpr size_t kTfLiteDefaultTensorAlignment = 64;
    constexpr size_t kInputBytes = 128 * 128 * 3;
    constexpr size_t kOutputBytes = 512 * 512 * 3;
    TensorProbeRun result;
    void* custom_input_ptr = nullptr;
    void* custom_output_ptr = nullptr;

    if (output_side != 128) {
        result.blockedStage = "unsupported_output_side";
        return result;
    }

    TfLiteModel* model = api.modelCreate(model_bytes.data(), model_bytes.size());
    if (model == nullptr) {
        result.blockedStage = "model_create";
        return result;
    }
    TfLiteInterpreterOptions* options = api.optionsCreate();
    if (options == nullptr) {
        api.modelDelete(model);
        result.blockedStage = "options_create";
        return result;
    }
    api.optionsSetThreads(options, 1);
    TfLiteInterpreter* interpreter = api.interpreterCreate(model, options);
    api.optionsDelete(options);
    if (interpreter == nullptr) {
        api.modelDelete(model);
        result.blockedStage = "interpreter_create";
        return result;
    }

    result.inputIndex = api.inputIndex(interpreter, 0);
    result.outputIndex = api.outputIndex(interpreter, 0);
    if (result.inputIndex < 0 || result.outputIndex < 0) {
        result.blockedStage = "tensor_index";
        api.interpreterDelete(interpreter);
        api.modelDelete(model);
        return result;
    }

    if (use_custom_allocation) {
        custom_input_ptr = alloc_mem(kInputBytes, kTfLiteDefaultTensorAlignment);
        custom_output_ptr = alloc_mem(kOutputBytes, kTfLiteDefaultTensorAlignment);
        if (custom_input_ptr == nullptr || custom_output_ptr == nullptr) {
            result.blockedStage = "custom_alloc";
            if (custom_input_ptr != nullptr) free_mem(custom_input_ptr);
            if (custom_output_ptr != nullptr) free_mem(custom_output_ptr);
            api.interpreterDelete(interpreter);
            api.modelDelete(model);
            return result;
        }
        TfLiteCustomAllocationNative input_alloc{custom_input_ptr, kInputBytes};
        TfLiteCustomAllocationNative output_alloc{custom_output_ptr, kOutputBytes};
        result.inputAllocStatus =
                api.setCustomAllocation(interpreter, result.inputIndex, &input_alloc, 0);
        result.outputAllocStatus =
                api.setCustomAllocation(interpreter, result.outputIndex, &output_alloc, 0);
    } else {
        result.inputAllocStatus = 0;
        result.outputAllocStatus = 0;
    }

    result.allocateStatus = api.allocateTensors(interpreter);
    TfLiteTensor* input_tensor = api.getInputTensor(interpreter, 0);
    const TfLiteTensor* output_tensor = api.getOutputTensor(interpreter, 0);
    void* input_ptr = input_tensor != nullptr ? api.tensorData(input_tensor) : nullptr;
    const void* output_ptr = output_tensor != nullptr ? api.tensorData(output_tensor) : nullptr;
    result.inputTensorBytes = input_tensor != nullptr ? api.tensorByteSize(input_tensor) : 0;
    result.outputTensorBytes = output_tensor != nullptr ? api.tensorByteSize(output_tensor) : 0;
    result.inputBound = use_custom_allocation ? input_ptr == custom_input_ptr : input_ptr != nullptr;
    result.outputBound = use_custom_allocation ? output_ptr == custom_output_ptr : output_ptr != nullptr;

    const auto delegate_start = std::chrono::steady_clock::now();
    result.delegateStatus =
            api.modifyGraph(interpreter, reinterpret_cast<TfLiteOpaqueDelegate*>(delegate_handle));
    const auto delegate_end = std::chrono::steady_clock::now();
    result.delegateUs = std::chrono::duration_cast<std::chrono::microseconds>(
            delegate_end - delegate_start).count();

    input_tensor = api.getInputTensor(interpreter, 0);
    output_tensor = api.getOutputTensor(interpreter, 0);
    input_ptr = input_tensor != nullptr ? api.tensorData(input_tensor) : input_ptr;
    output_ptr = output_tensor != nullptr ? api.tensorData(output_tensor) : output_ptr;
    result.inputTensorBytes = input_tensor != nullptr ? api.tensorByteSize(input_tensor) : result.inputTensorBytes;
    result.outputTensorBytes = output_tensor != nullptr ? api.tensorByteSize(output_tensor) : result.outputTensorBytes;
    result.inputBound = use_custom_allocation ? input_ptr == custom_input_ptr : input_ptr != nullptr;
    result.outputBound = use_custom_allocation ? output_ptr == custom_output_ptr : output_ptr != nullptr;

    const auto fill_start = std::chrono::steady_clock::now();
    const bool filled = fillDirectYuvRoiRgb(
            y_bytes,
            u_bytes,
            v_bytes,
            width,
            height,
            y_row_stride,
            y_pixel_stride,
            u_row_stride,
            u_pixel_stride,
            v_row_stride,
            v_pixel_stride,
            output_side,
            rotation_degrees,
            reinterpret_cast<uint8_t*>(input_ptr));
    const auto fill_end = std::chrono::steady_clock::now();
    result.inputFillUs = std::chrono::duration_cast<std::chrono::microseconds>(
            fill_end - fill_start).count();
    if (!filled) {
        result.blockedStage = "fill_yuv_input";
    }

    std::vector<int64_t> invoke_times_us;
    result.invokeStatus = result.delegateStatus;
    if (filled && result.delegateStatus == 0) {
        for (int i = 0; i < repeats; ++i) {
            const auto invoke_start = std::chrono::steady_clock::now();
            result.invokeStatus = api.invoke(interpreter);
            const auto invoke_end = std::chrono::steady_clock::now();
            invoke_times_us.push_back(std::chrono::duration_cast<std::chrono::microseconds>(
                    invoke_end - invoke_start).count());
            if (result.invokeStatus != 0) {
                break;
            }
        }
    }
    result.completedRuns = invoke_times_us.size();
    result.invokeAvgUs = averageMicros(invoke_times_us);
    result.invokeMinUs = minMicros(invoke_times_us);
    result.invokeMaxUs = maxMicros(invoke_times_us);
    result.outputSample = sampleOutputBytes(
            reinterpret_cast<const uint8_t*>(output_ptr),
            std::min(result.outputTensorBytes, kOutputBytes));
    result.passed = result.inputAllocStatus == 0 && result.outputAllocStatus == 0 &&
                    result.allocateStatus == 0 && result.delegateStatus == 0 &&
                    result.invokeStatus == 0 && result.inputBound && result.outputBound &&
                    filled &&
                    result.inputTensorBytes <= kInputBytes &&
                    result.outputTensorBytes <= kOutputBytes;

    api.interpreterDelete(interpreter);
    api.modelDelete(model);
    if (custom_input_ptr != nullptr) free_mem(custom_input_ptr);
    if (custom_output_ptr != nullptr) free_mem(custom_output_ptr);
    return result;
}

std::string qnnDelegateSharedCameraTensorCompareProbe(
        JNIEnv* env,
        jobject asset_manager,
        const char* model_asset,
        intptr_t normal_delegate_handle,
        intptr_t shared_delegate_handle,
        jobject y_buffer,
        jobject u_buffer,
        jobject v_buffer,
        int width,
        int height,
        int y_row_stride,
        int y_pixel_stride,
        int u_row_stride,
        int u_pixel_stride,
        int v_row_stride,
        int v_pixel_stride,
        int output_side,
        int rotation_degrees,
        int repeats) {
    if (normal_delegate_handle == 0 || shared_delegate_handle == 0 ||
        y_buffer == nullptr || u_buffer == nullptr || v_buffer == nullptr) {
        return "status=blocked stage=argument error=null_input";
    }
    const auto* y_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(y_buffer));
    const auto* u_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(u_buffer));
    const auto* v_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(v_buffer));
    if (y_bytes == nullptr || u_bytes == nullptr || v_bytes == nullptr) {
        return "status=blocked stage=direct_buffer error=null_address";
    }

    std::vector<uint8_t> model_bytes;
    if (!readAssetBytes(env, asset_manager, model_asset, model_bytes)) {
        return "status=blocked stage=asset error=read_model_failed";
    }
    DynamicLibrary tflite("libtensorflowlite_jni.so");
    if (tflite.handle == nullptr) {
        return "status=blocked stage=dlopen library=libtensorflowlite_jni.so";
    }
    DynamicLibrary qnn("libQnnTFLiteDelegate.so");
    if (qnn.handle == nullptr) {
        return "status=blocked stage=dlopen library=libQnnTFLiteDelegate.so";
    }
    const TfLiteApi api = loadTfLiteApi(tflite.handle);
    auto alloc_mem = loadSymbol<QnnDelegateAllocCustomMemFn>(qnn.handle, "TfLiteQnnDelegateAllocCustomMem");
    auto free_mem = loadSymbol<QnnDelegateFreeCustomMemFn>(qnn.handle, "TfLiteQnnDelegateFreeCustomMem");
    if (!hasRequiredTfLiteApi(api, true) || alloc_mem == nullptr || free_mem == nullptr) {
        return "status=blocked stage=dlsym error=missing_tflite_or_qnn_symbol";
    }

    const int safe_repeats = std::max(1, repeats);
    TensorProbeRun normal = runCameraTensorProbeVariant(
            api, model_bytes, normal_delegate_handle, false, alloc_mem, free_mem, safe_repeats,
            y_bytes, u_bytes, v_bytes, width, height,
            y_row_stride, y_pixel_stride, u_row_stride, u_pixel_stride, v_row_stride, v_pixel_stride,
            output_side, rotation_degrees);
    TensorProbeRun shared = runCameraTensorProbeVariant(
            api, model_bytes, shared_delegate_handle, true, alloc_mem, free_mem, safe_repeats,
            y_bytes, u_bytes, v_bytes, width, height,
            y_row_stride, y_pixel_stride, u_row_stride, u_pixel_stride, v_row_stride, v_pixel_stride,
            output_side, rotation_degrees);
    const bool checksum_match = normal.outputSample.checksum == shared.outputSample.checksum;
    const int64_t fill_delta_us =
            (shared.inputFillUs >= 0 && normal.inputFillUs >= 0)
            ? shared.inputFillUs - normal.inputFillUs
            : 0;
    const int64_t invoke_delta_us =
            (shared.invokeAvgUs >= 0 && normal.invokeAvgUs >= 0)
            ? shared.invokeAvgUs - normal.invokeAvgUs
            : 0;
    const bool passed = normal.passed && shared.passed && checksum_match;

    char result[4096];
    snprintf(result, sizeof(result),
             "status=%s stage=camera_tensor_buffer_compare modelBytes=%zu repeats=%d "
             "frame=%dx%d outputSide=%d rotation=%d "
             "normalPass=%s normalStage=%s normalDelegate=%d normalInvoke=%d "
             "normalInputBound=%s normalOutputBound=%s normalChecksum=%u "
             "normalCompletedRuns=%zu normalInputFillUs=%lld normalDelegateUs=%lld "
             "normalInvokeAvgUs=%lld normalInvokeMinUs=%lld normalInvokeMaxUs=%lld "
             "sharedPass=%s sharedStage=%s sharedDelegate=%d sharedInvoke=%d "
             "sharedInputBound=%s sharedOutputBound=%s sharedChecksum=%u "
             "sharedCompletedRuns=%zu sharedInputFillUs=%lld sharedDelegateUs=%lld "
             "sharedInvokeAvgUs=%lld sharedInvokeMinUs=%lld sharedInvokeMaxUs=%lld "
             "checksumMatch=%s inputFillDeltaUs=%lld invokeAvgDeltaUs=%lld",
             passed ? "pass" : "blocked",
             model_bytes.size(),
             safe_repeats,
             width,
             height,
             output_side,
             normalizeRotation(rotation_degrees),
             normal.passed ? "true" : "false",
             normal.blockedStage.empty() ? "ok" : normal.blockedStage.c_str(),
             normal.delegateStatus,
             normal.invokeStatus,
             normal.inputBound ? "true" : "false",
             normal.outputBound ? "true" : "false",
             normal.outputSample.checksum,
             normal.completedRuns,
             static_cast<long long>(normal.inputFillUs),
             static_cast<long long>(normal.delegateUs),
             static_cast<long long>(normal.invokeAvgUs),
             static_cast<long long>(normal.invokeMinUs),
             static_cast<long long>(normal.invokeMaxUs),
             shared.passed ? "true" : "false",
             shared.blockedStage.empty() ? "ok" : shared.blockedStage.c_str(),
             shared.delegateStatus,
             shared.invokeStatus,
             shared.inputBound ? "true" : "false",
             shared.outputBound ? "true" : "false",
             shared.outputSample.checksum,
             shared.completedRuns,
             static_cast<long long>(shared.inputFillUs),
             static_cast<long long>(shared.delegateUs),
             static_cast<long long>(shared.invokeAvgUs),
             static_cast<long long>(shared.invokeMinUs),
             static_cast<long long>(shared.invokeMaxUs),
             checksum_match ? "true" : "false",
             static_cast<long long>(fill_delta_us),
             static_cast<long long>(invoke_delta_us));
    return result;
}

std::string qnnDelegateSharedTensorCompareProbe(
        JNIEnv* env,
        jobject asset_manager,
        const char* model_asset,
        intptr_t normal_delegate_handle,
        intptr_t shared_delegate_handle,
        int repeats) {
    if (normal_delegate_handle == 0 || shared_delegate_handle == 0) {
        return "status=blocked stage=argument error=null_delegate_handle";
    }
    std::vector<uint8_t> model_bytes;
    if (!readAssetBytes(env, asset_manager, model_asset, model_bytes)) {
        return "status=blocked stage=asset error=read_model_failed";
    }
    DynamicLibrary tflite("libtensorflowlite_jni.so");
    if (tflite.handle == nullptr) {
        return "status=blocked stage=dlopen library=libtensorflowlite_jni.so";
    }
    DynamicLibrary qnn("libQnnTFLiteDelegate.so");
    if (qnn.handle == nullptr) {
        return "status=blocked stage=dlopen library=libQnnTFLiteDelegate.so";
    }
    const TfLiteApi api = loadTfLiteApi(tflite.handle);
    auto alloc_mem = loadSymbol<QnnDelegateAllocCustomMemFn>(qnn.handle, "TfLiteQnnDelegateAllocCustomMem");
    auto free_mem = loadSymbol<QnnDelegateFreeCustomMemFn>(qnn.handle, "TfLiteQnnDelegateFreeCustomMem");
    if (!hasRequiredTfLiteApi(api, true) || alloc_mem == nullptr || free_mem == nullptr) {
        return "status=blocked stage=dlsym error=missing_tflite_or_qnn_symbol";
    }

    const int safe_repeats = std::max(1, repeats);
    TensorProbeRun normal = runTensorProbeVariant(
            api, model_bytes, normal_delegate_handle, false, alloc_mem, free_mem, safe_repeats);
    TensorProbeRun shared = runTensorProbeVariant(
            api, model_bytes, shared_delegate_handle, true, alloc_mem, free_mem, safe_repeats);
    const bool checksum_match = normal.outputSample.checksum == shared.outputSample.checksum;
    const int64_t avg_delta_us =
            (shared.invokeAvgUs >= 0 && normal.invokeAvgUs >= 0)
            ? shared.invokeAvgUs - normal.invokeAvgUs
            : 0;
    const bool passed = normal.passed && shared.passed && checksum_match;

    char result[3072];
    snprintf(result, sizeof(result),
             "status=%s stage=tensor_buffer_compare modelBytes=%zu repeats=%d "
             "normalPass=%s normalStage=%s normalDelegate=%d normalInvoke=%d "
             "normalInputBound=%s normalOutputBound=%s normalChecksum=%u "
             "normalCompletedRuns=%zu normalDelegateUs=%lld normalInvokeAvgUs=%lld "
             "normalInvokeMinUs=%lld normalInvokeMaxUs=%lld "
             "sharedPass=%s sharedStage=%s sharedDelegate=%d sharedInvoke=%d "
             "sharedInputBound=%s sharedOutputBound=%s sharedChecksum=%u "
             "sharedCompletedRuns=%zu sharedDelegateUs=%lld sharedInvokeAvgUs=%lld "
             "sharedInvokeMinUs=%lld sharedInvokeMaxUs=%lld "
             "checksumMatch=%s invokeAvgDeltaUs=%lld",
             passed ? "pass" : "blocked",
             model_bytes.size(),
             safe_repeats,
             normal.passed ? "true" : "false",
             normal.blockedStage.empty() ? "ok" : normal.blockedStage.c_str(),
             normal.delegateStatus,
             normal.invokeStatus,
             normal.inputBound ? "true" : "false",
             normal.outputBound ? "true" : "false",
             normal.outputSample.checksum,
             normal.completedRuns,
             static_cast<long long>(normal.delegateUs),
             static_cast<long long>(normal.invokeAvgUs),
             static_cast<long long>(normal.invokeMinUs),
             static_cast<long long>(normal.invokeMaxUs),
             shared.passed ? "true" : "false",
             shared.blockedStage.empty() ? "ok" : shared.blockedStage.c_str(),
             shared.delegateStatus,
             shared.invokeStatus,
             shared.inputBound ? "true" : "false",
             shared.outputBound ? "true" : "false",
             shared.outputSample.checksum,
             shared.completedRuns,
             static_cast<long long>(shared.delegateUs),
             static_cast<long long>(shared.invokeAvgUs),
             static_cast<long long>(shared.invokeMinUs),
             static_cast<long long>(shared.invokeMaxUs),
             checksum_match ? "true" : "false",
             static_cast<long long>(avg_delta_us));
    return result;
}

int clampToByte(float value) {
    return std::max(0, std::min(255, static_cast<int>(value)));
}

int yuvToArgb(int y, int u, int v) {
    const int c = y;
    const int d = u - 128;
    const int e = v - 128;
    const int r = clampToByte((256 * c + 359 * e + 128) >> 8);
    const int g = clampToByte((256 * c - 88 * d - 183 * e + 128) >> 8);
    const int b = clampToByte((256 * c + 454 * d + 128) >> 8);
    return static_cast<int>(0xFF000000u | (static_cast<unsigned int>(r) << 16)
            | (static_cast<unsigned int>(g) << 8) | static_cast<unsigned int>(b));
}

void yuvToRgb(int y, int u, int v, jbyte* out) {
    const int c = y;
    const int d = u - 128;
    const int e = v - 128;
    out[0] = static_cast<jbyte>(clampToByte((256 * c + 359 * e + 128) >> 8));
    out[1] = static_cast<jbyte>(clampToByte((256 * c - 88 * d - 183 * e + 128) >> 8));
    out[2] = static_cast<jbyte>(clampToByte((256 * c + 454 * d + 128) >> 8));
}

int normalizeRotation(int rotation_degrees) {
    int normalized = rotation_degrees % 360;
    if (normalized < 0) {
        normalized += 360;
    }
    return normalized;
}

int rotatedOutputIndex(int x, int y, int side, int rotation_degrees) {
    switch (normalizeRotation(rotation_degrees)) {
        case 90:
            return x * side + (side - 1 - y);
        case 180:
            return (side - 1 - y) * side + (side - 1 - x);
        case 270:
            return (side - 1 - x) * side + y;
        default:
            return y * side + x;
    }
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
Java_com_cyf_rb5visionlab_MainActivity_qnnSharedMemoryTensorProbe(
        JNIEnv* env,
        jobject /* thiz */,
        jobject asset_manager,
        jstring model_asset,
        jlong delegate_handle,
        jint repeats) {
    if (asset_manager == nullptr || model_asset == nullptr || delegate_handle == 0) {
        return env->NewStringUTF("status=blocked stage=argument error=null_input");
    }
    const char* model_asset_chars = env->GetStringUTFChars(model_asset, nullptr);
    if (model_asset_chars == nullptr) {
        return env->NewStringUTF("status=blocked stage=argument error=model_asset_string");
    }
    const std::string result = qnnDelegateSharedTensorProbe(
            env,
            asset_manager,
            model_asset_chars,
            static_cast<intptr_t>(delegate_handle),
            std::max(1, static_cast<int>(repeats)));
    env->ReleaseStringUTFChars(model_asset, model_asset_chars);
    LOGD("qnnSharedMemoryTensorProbe %s", result.c_str());
    return env->NewStringUTF(result.c_str());
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_qnnSharedMemoryTensorCompareProbe(
        JNIEnv* env,
        jobject /* thiz */,
        jobject asset_manager,
        jstring model_asset,
        jlong normal_delegate_handle,
        jlong shared_delegate_handle,
        jint repeats) {
    if (asset_manager == nullptr || model_asset == nullptr ||
        normal_delegate_handle == 0 || shared_delegate_handle == 0) {
        return env->NewStringUTF("status=blocked stage=argument error=null_input");
    }
    const char* model_asset_chars = env->GetStringUTFChars(model_asset, nullptr);
    if (model_asset_chars == nullptr) {
        return env->NewStringUTF("status=blocked stage=argument error=model_asset_string");
    }
    const std::string result = qnnDelegateSharedTensorCompareProbe(
            env,
            asset_manager,
            model_asset_chars,
            static_cast<intptr_t>(normal_delegate_handle),
            static_cast<intptr_t>(shared_delegate_handle),
            std::max(1, static_cast<int>(repeats)));
    env->ReleaseStringUTFChars(model_asset, model_asset_chars);
    LOGD("qnnSharedMemoryTensorCompareProbe %s", result.c_str());
    return env->NewStringUTF(result.c_str());
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_qnnSharedCameraTensorCompareProbe(
        JNIEnv* env,
        jobject /* thiz */,
        jobject asset_manager,
        jstring model_asset,
        jlong normal_delegate_handle,
        jlong shared_delegate_handle,
        jobject y_buffer,
        jobject u_buffer,
        jobject v_buffer,
        jint width,
        jint height,
        jint y_row_stride,
        jint y_pixel_stride,
        jint u_row_stride,
        jint u_pixel_stride,
        jint v_row_stride,
        jint v_pixel_stride,
        jint output_side,
        jint rotation_degrees,
        jint repeats) {
    if (asset_manager == nullptr || model_asset == nullptr ||
        normal_delegate_handle == 0 || shared_delegate_handle == 0 ||
        y_buffer == nullptr || u_buffer == nullptr || v_buffer == nullptr) {
        return env->NewStringUTF("status=blocked stage=argument error=null_input");
    }
    const char* model_asset_chars = env->GetStringUTFChars(model_asset, nullptr);
    if (model_asset_chars == nullptr) {
        return env->NewStringUTF("status=blocked stage=argument error=model_asset_string");
    }
    const std::string result = qnnDelegateSharedCameraTensorCompareProbe(
            env,
            asset_manager,
            model_asset_chars,
            static_cast<intptr_t>(normal_delegate_handle),
            static_cast<intptr_t>(shared_delegate_handle),
            y_buffer,
            u_buffer,
            v_buffer,
            width,
            height,
            y_row_stride,
            y_pixel_stride,
            u_row_stride,
            u_pixel_stride,
            v_row_stride,
            v_pixel_stride,
            output_side,
            rotation_degrees,
            std::max(1, static_cast<int>(repeats)));
    env->ReleaseStringUTFChars(model_asset, model_asset_chars);
    LOGD("qnnSharedCameraTensorCompareProbe %s", result.c_str());
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
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_directBufferProbe(
        JNIEnv* env,
        jobject /* thiz */,
        jobject y_buffer,
        jobject u_buffer,
        jobject v_buffer) {
    auto describe = [env](const char* name, jobject buffer) -> std::string {
        if (buffer == nullptr) {
            return std::string(name) + "=null";
        }
        void* address = env->GetDirectBufferAddress(buffer);
        const jlong capacity = env->GetDirectBufferCapacity(buffer);
        char text[160];
        snprintf(text, sizeof(text), "%sDirectAddress=%s %sCapacity=%lld",
                 name,
                 address != nullptr ? "non_null" : "null",
                 name,
                 static_cast<long long>(capacity));
        return text;
    };
    const std::string result =
            describe("y", y_buffer) + " " +
            describe("u", u_buffer) + " " +
            describe("v", v_buffer);
    LOGD("directBufferProbe %s", result.c_str());
    return env->NewStringUTF(result.c_str());
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_hardwareBufferProbe(
        JNIEnv* env,
        jobject /* thiz */,
        jobject hardware_buffer,
        jint image_width,
        jint image_height,
        jint image_format) {
    if (hardware_buffer == nullptr) {
        return env->NewStringUTF("status=blocked stage=java_image hardwareBuffer=null");
    }

    AHardwareBuffer* buffer = AHardwareBuffer_fromHardwareBuffer(env, hardware_buffer);
    if (buffer == nullptr) {
        return env->NewStringUTF("status=blocked stage=fromHardwareBuffer hardwareBuffer=null");
    }

    AHardwareBuffer_Desc desc{};
    AHardwareBuffer_describe(buffer, &desc);

    AHardwareBuffer_Planes planes{};
    const int lock_status = AHardwareBuffer_lockPlanes(
            buffer,
            AHARDWAREBUFFER_USAGE_CPU_READ_OFTEN,
            -1,
            nullptr,
            &planes);
    uint32_t plane_count = 0;
    uint32_t plane0_row_stride = 0;
    uint32_t plane0_pixel_stride = 0;
    bool plane0_data = false;
    if (lock_status == 0) {
        plane_count = planes.planeCount;
        if (planes.planeCount > 0) {
            plane0_row_stride = planes.planes[0].rowStride;
            plane0_pixel_stride = planes.planes[0].pixelStride;
            plane0_data = planes.planes[0].data != nullptr;
        }
        AHardwareBuffer_unlock(buffer, nullptr);
    }

    char result[768];
    snprintf(result, sizeof(result),
             "status=pass stage=hardware_buffer image=%dx%d imageFormat=%d "
             "descWidth=%u descHeight=%u descLayers=%u descFormat=%u descUsage=%llu descStride=%u "
             "lockPlanes=%d planeCount=%u plane0RowStride=%u plane0PixelStride=%u plane0Data=%s",
             image_width,
             image_height,
             image_format,
             desc.width,
             desc.height,
             desc.layers,
             desc.format,
             static_cast<unsigned long long>(desc.usage),
             desc.stride,
             lock_status,
             plane_count,
             plane0_row_stride,
             plane0_pixel_stride,
             plane0_data ? "true" : "false");
    LOGD("hardwareBufferProbe %s", result);
    return env->NewStringUTF(result);
}

extern "C"
JNIEXPORT jbyteArray JNICALL
Java_com_cyf_rb5visionlab_MainActivity_nativeYuvToRgbRoiBytesRotatedDirect(
        JNIEnv* env,
        jobject /* thiz */,
        jobject y_buffer,
        jobject u_buffer,
        jobject v_buffer,
        jint width,
        jint height,
        jint y_row_stride,
        jint y_pixel_stride,
        jint u_row_stride,
        jint u_pixel_stride,
        jint v_row_stride,
        jint v_pixel_stride,
        jint output_side,
        jint rotation_degrees) {
    if (y_buffer == nullptr || u_buffer == nullptr || v_buffer == nullptr ||
        width <= 0 || height <= 0 || output_side <= 0 ||
        y_row_stride <= 0 || u_row_stride <= 0 || v_row_stride <= 0 ||
        y_pixel_stride <= 0 || u_pixel_stride <= 0 || v_pixel_stride <= 0) {
        return nullptr;
    }

    const auto* y_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(y_buffer));
    const auto* u_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(u_buffer));
    const auto* v_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(v_buffer));
    if (y_bytes == nullptr || u_bytes == nullptr || v_bytes == nullptr) {
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
            const int y_value = y_bytes[y_base + src_x * y_pixel_stride];
            const int u_value = u_bytes[u_base + uv_x * u_pixel_stride];
            const int v_value = v_bytes[v_base + uv_x * v_pixel_stride];
            const int out = rotatedOutputIndex(ox, oy, output_side, rotation_degrees) * 3;
            yuvToRgb(y_value, u_value, v_value, rgb.data() + out);
        }
    }

    env->SetByteArrayRegion(result, 0, byte_count, rgb.data());
    LOGD("nativeYuvToRgbRoiBytesRotatedDirect width=%d height=%d crop=%d output=%d rotation=%d",
         width, height, crop_side, output_side, normalizeRotation(rotation_degrees));
    return result;
}

extern "C"
JNIEXPORT jboolean JNICALL
Java_com_cyf_rb5visionlab_MainActivity_nativeYuvToRgbRoiBytesRotatedDirectInto(
        JNIEnv* env,
        jobject /* thiz */,
        jobject y_buffer,
        jobject u_buffer,
        jobject v_buffer,
        jint width,
        jint height,
        jint y_row_stride,
        jint y_pixel_stride,
        jint u_row_stride,
        jint u_pixel_stride,
        jint v_row_stride,
        jint v_pixel_stride,
        jint output_side,
        jint rotation_degrees,
        jbyteArray output) {
    if (y_buffer == nullptr || u_buffer == nullptr || v_buffer == nullptr || output == nullptr ||
        width <= 0 || height <= 0 || output_side <= 0 ||
        y_row_stride <= 0 || u_row_stride <= 0 || v_row_stride <= 0 ||
        y_pixel_stride <= 0 || u_pixel_stride <= 0 || v_pixel_stride <= 0) {
        return JNI_FALSE;
    }

    const int byte_count = output_side * output_side * 3;
    if (env->GetArrayLength(output) < byte_count) {
        return JNI_FALSE;
    }

    const auto* y_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(y_buffer));
    const auto* u_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(u_buffer));
    const auto* v_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(v_buffer));
    if (y_bytes == nullptr || u_bytes == nullptr || v_bytes == nullptr) {
        return JNI_FALSE;
    }

    jbyte* out_bytes = env->GetByteArrayElements(output, nullptr);
    if (out_bytes == nullptr) {
        return JNI_FALSE;
    }

    const int crop_side = std::max(
            output_side,
            std::min({width * output_side / 640, width, height}));
    const int left = (width - crop_side) / 2;
    const int top = (height - crop_side) / 2;
    for (int oy = 0; oy < output_side; ++oy) {
        const int src_y = top + (oy * crop_side + crop_side / (output_side * 2)) / output_side;
        const int y_base = src_y * y_row_stride;
        const int uv_y = src_y / 2;
        const int u_base = uv_y * u_row_stride;
        const int v_base = uv_y * v_row_stride;
        for (int ox = 0; ox < output_side; ++ox) {
            const int src_x = left + (ox * crop_side + crop_side / (output_side * 2)) / output_side;
            const int uv_x = src_x / 2;
            const int y_value = y_bytes[y_base + src_x * y_pixel_stride];
            const int u_value = u_bytes[u_base + uv_x * u_pixel_stride];
            const int v_value = v_bytes[v_base + uv_x * v_pixel_stride];
            const int out = rotatedOutputIndex(ox, oy, output_side, rotation_degrees) * 3;
            yuvToRgb(y_value, u_value, v_value, out_bytes + out);
        }
    }

    env->ReleaseByteArrayElements(output, out_bytes, 0);
    LOGD("nativeYuvToRgbRoiBytesRotatedDirectInto width=%d height=%d crop=%d output=%d rotation=%d",
         width, height, crop_side, output_side, normalizeRotation(rotation_degrees));
    return JNI_TRUE;
}

extern "C"
JNIEXPORT jstring JNICALL
Java_com_cyf_rb5visionlab_MainActivity_nativeYuvToRgbRoiBytesRotatedDirectBreakdown(
        JNIEnv* env,
        jobject /* thiz */,
        jobject y_buffer,
        jobject u_buffer,
        jobject v_buffer,
        jint width,
        jint height,
        jint y_row_stride,
        jint y_pixel_stride,
        jint u_row_stride,
        jint u_pixel_stride,
        jint v_row_stride,
        jint v_pixel_stride,
        jint output_side,
        jint rotation_degrees,
        jbyteArray output) {
    const auto t_total0 = std::chrono::steady_clock::now();
    if (y_buffer == nullptr || u_buffer == nullptr || v_buffer == nullptr || output == nullptr ||
        width <= 0 || height <= 0 || output_side <= 0 ||
        y_row_stride <= 0 || u_row_stride <= 0 || v_row_stride <= 0 ||
        y_pixel_stride <= 0 || u_pixel_stride <= 0 || v_pixel_stride <= 0) {
        return env->NewStringUTF("status=blocked stage=argument");
    }

    const int byte_count = output_side * output_side * 3;
    if (env->GetArrayLength(output) < byte_count) {
        return env->NewStringUTF("status=blocked stage=output_size");
    }

    const auto t_addr0 = std::chrono::steady_clock::now();
    const auto* y_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(y_buffer));
    const auto* u_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(u_buffer));
    const auto* v_bytes = static_cast<const uint8_t*>(env->GetDirectBufferAddress(v_buffer));
    const auto t_addr1 = std::chrono::steady_clock::now();
    if (y_bytes == nullptr || u_bytes == nullptr || v_bytes == nullptr) {
        return env->NewStringUTF("status=blocked stage=direct_buffer");
    }

    const auto t_pin0 = std::chrono::steady_clock::now();
    jbyte* out_bytes = env->GetByteArrayElements(output, nullptr);
    const auto t_pin1 = std::chrono::steady_clock::now();
    if (out_bytes == nullptr) {
        return env->NewStringUTF("status=blocked stage=output_pin");
    }

    const int crop_side = std::max(
            output_side,
            std::min({width * output_side / 640, width, height}));
    const int left = (width - crop_side) / 2;
    const int top = (height - crop_side) / 2;

    const auto t_loop0 = std::chrono::steady_clock::now();
    for (int oy = 0; oy < output_side; ++oy) {
        const int src_y = top + (oy * crop_side + crop_side / (output_side * 2)) / output_side;
        const int y_base = src_y * y_row_stride;
        const int uv_y = src_y / 2;
        const int u_base = uv_y * u_row_stride;
        const int v_base = uv_y * v_row_stride;
        for (int ox = 0; ox < output_side; ++ox) {
            const int src_x = left + (ox * crop_side + crop_side / (output_side * 2)) / output_side;
            const int uv_x = src_x / 2;
            const int y_value = y_bytes[y_base + src_x * y_pixel_stride];
            const int u_value = u_bytes[u_base + uv_x * u_pixel_stride];
            const int v_value = v_bytes[v_base + uv_x * v_pixel_stride];
            const int out = rotatedOutputIndex(ox, oy, output_side, rotation_degrees) * 3;
            yuvToRgb(y_value, u_value, v_value, out_bytes + out);
        }
    }
    const auto t_loop1 = std::chrono::steady_clock::now();

    const auto t_release0 = std::chrono::steady_clock::now();
    env->ReleaseByteArrayElements(output, out_bytes, 0);
    const auto t_release1 = std::chrono::steady_clock::now();
    const auto t_total1 = std::chrono::steady_clock::now();

    const int64_t address_us = std::chrono::duration_cast<std::chrono::microseconds>(t_addr1 - t_addr0).count();
    const int64_t output_pin_us = std::chrono::duration_cast<std::chrono::microseconds>(t_pin1 - t_pin0).count();
    const int64_t loop_us = std::chrono::duration_cast<std::chrono::microseconds>(t_loop1 - t_loop0).count();
    const int64_t release_us = std::chrono::duration_cast<std::chrono::microseconds>(t_release1 - t_release0).count();
    const int64_t total_us = std::chrono::duration_cast<std::chrono::microseconds>(t_total1 - t_total0).count();

    char result[768];
    snprintf(result, sizeof(result),
             "status=pass stage=direct_yuv_breakdown frame=%dx%d crop=%d output=%d rotation=%d "
             "addressUs=%lld outputPinUs=%lld loopUs=%lld releaseUs=%lld totalUs=%lld",
             width,
             height,
             crop_side,
             output_side,
             normalizeRotation(rotation_degrees),
             static_cast<long long>(address_us),
             static_cast<long long>(output_pin_us),
             static_cast<long long>(loop_us),
             static_cast<long long>(release_us),
             static_cast<long long>(total_us));
    LOGD("nativeYuvToRgbRoiBytesRotatedDirectBreakdown %s", result);
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
            const int out = (oy * output_side + ox) * 3;
            yuvToRgb(y_value, u_value, v_value, rgb.data() + out);
        }
    }

    env->SetByteArrayRegion(result, 0, byte_count, rgb.data());
    env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);
    env->ReleaseByteArrayElements(u_data, u_bytes, JNI_ABORT);
    env->ReleaseByteArrayElements(v_data, v_bytes, JNI_ABORT);
    LOGD("nativeYuvToRgbRoiBytes width=%d height=%d crop=%d output=%d", width, height, crop_side, output_side);
    return result;
}

extern "C"
JNIEXPORT jbyteArray JNICALL
Java_com_cyf_rb5visionlab_MainActivity_nativeYuvToRgbRoiBytesRotated(
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
        jint output_side,
        jint rotation_degrees) {
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
            const int out = rotatedOutputIndex(ox, oy, output_side, rotation_degrees) * 3;
            yuvToRgb(y_value, u_value, v_value, rgb.data() + out);
        }
    }

    env->SetByteArrayRegion(result, 0, byte_count, rgb.data());
    env->ReleaseByteArrayElements(y_data, y_bytes, JNI_ABORT);
    env->ReleaseByteArrayElements(u_data, u_bytes, JNI_ABORT);
    env->ReleaseByteArrayElements(v_data, v_bytes, JNI_ABORT);
    LOGD("nativeYuvToRgbRoiBytesRotated width=%d height=%d crop=%d output=%d rotation=%d",
         width, height, crop_side, output_side, normalizeRotation(rotation_degrees));
    return result;
}
