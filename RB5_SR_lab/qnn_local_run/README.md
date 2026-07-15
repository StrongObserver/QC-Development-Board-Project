# Local QNN Run Materials

This folder contains the host-side files needed to run the AI Hub generated
Real-ESRGAN W8A8 QNN context binary on the local RB5 device with `qnn-net-run`.

Current state:

- RB5 is connected over ADB as `ff5d3ab4`.
- Device is Android 13 / `kalama` / QCS8550 / `arm64-v8a`.
- Device `/vendor/lib64` has QNN runtime libraries.
- Device `/vendor/lib/rfsa/adsp` has `libQnnHtpV73Skel.so`.
- Local QAIRT SDK is available at:
  `C:\Qualcomm\QAIRT\v2.45.0.260326\qairt\2.45.0.260326`

The SDK matches the context binary version:

```text
QAIRT 2.45.0.260326154327
```

Run:

```powershell
.\run_qnn_net_run.ps1 -QairtRoot "C:\Qualcomm\QAIRT\v2.45.0.260326\qairt\2.45.0.260326"
```

The script stages everything under:

```text
/data/local/tmp/qnn_sr
```

It does not modify system/vendor partitions.

Important RB5-specific finding:

- Do not force `ADSP_LIBRARY_PATH`.
- On this RB5 image, leaving `ADSP_LIBRARY_PATH` unset lets the system load the compatible vendor HTP v73 skel.
- Forcing either local or vendor `ADSP_LIBRARY_PATH` caused `Device Creation failure` and `QNN_TRANSPORT_CONFIG crc32 failed`.

## Files

```text
input.raw
input_list.txt
run_qnn_net_run.ps1
convert_qnn_output.py
```

`input.raw` is NHWC RGB uint8 with shape `[1,128,128,3]`.

Expected output raw:

```text
output/Result_0/upscaled_image.raw
```

The output tensor is `[1,512,512,3] uint8` with:

```text
scale=0.005237185396254063
zero_point=25
```

Known good local run evidence:

```text
qnn-net-run build version: v2.45.0.260326154327
Creating context from binary file: real_esrgan_general_x4v3.bin
Executing Graphs
Finished Executing Graphs
output/Result_0/upscaled_image_native.raw = 786432 bytes
```
