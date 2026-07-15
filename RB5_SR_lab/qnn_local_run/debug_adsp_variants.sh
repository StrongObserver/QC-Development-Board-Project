#!/system/bin/sh

BASE=/data/local/tmp/qnn_sr
cd "$BASE" || exit 1

run_case() {
  name="$1"
  adsp="$2"
  echo "===== $name ====="
  rm -rf output
  mkdir -p output
  if [ "$adsp" = "__UNSET__" ]; then
    unset ADSP_LIBRARY_PATH
    echo "ADSP_LIBRARY_PATH=<unset>"
  else
    export ADSP_LIBRARY_PATH="$adsp"
    echo "ADSP_LIBRARY_PATH=$ADSP_LIBRARY_PATH"
  fi
  export LD_LIBRARY_PATH="$BASE:/vendor/lib64:${LD_LIBRARY_PATH:-}"
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
  rc=$?
  find output -maxdepth 2 -type f -print -exec ls -l {} \; 2>/dev/null
  echo "RESULT $name rc=$rc"
}

run_case "unset_adsp" "__UNSET__"
run_case "vendor_adsp" "/vendor/lib/rfsa/adsp:/vendor/dsp/cdsp:/system/lib/rfsa/adsp:/dsp"
run_case "local_then_vendor_adsp" "$BASE:/vendor/lib/rfsa/adsp:/vendor/dsp/cdsp:/system/lib/rfsa/adsp:/dsp"
