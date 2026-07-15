#!/system/bin/sh
set -eu

cd /data/local/tmp/qnn_sr
rm -rf output
mkdir -p output

export LD_LIBRARY_PATH=/data/local/tmp/qnn_sr:/vendor/lib64:${LD_LIBRARY_PATH:-}
# Do not set ADSP_LIBRARY_PATH here. On this RB5 image, the default vendor
# search path loads the compatible HTP v73 skel successfully, while forcing
# local/vendor ADSP_LIBRARY_PATH causes QNN Device Creation failure.
unset ADSP_LIBRARY_PATH

./qnn-net-run \
  --backend libQnnHtp.so \
  --retrieve_context real_esrgan_general_x4v3.bin \
  --input_list input_list.txt \
  --output_dir output \
  --profiling_level detailed \
  --log_level verbose \
  --config_file HtpConfigFile.json \
  --use_native_input_files \
  --use_native_output_files \
  --device_options "device_id:0;core_id:0"

if [ -f output/qnn-profiling-data_0.log ]; then
  ./qnn-profile-viewer \
    --input_log output/qnn-profiling-data_0.log \
    --output output/profile_viewer.csv \
    > output/profile_viewer_stdout.txt 2>&1 || true
fi
