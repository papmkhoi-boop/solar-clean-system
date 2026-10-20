import sys
import traceback

print("Starting debug runner...")
try:
    import solar_panel_plc_auto_tflite
    solar_panel_plc_auto_tflite.main()
except BaseException as e:
    with open('crash.log', 'w') as f:
        f.write(f"Exception type: {type(e)}\n")
        f.write(f"Exception: {e}\n")
        traceback.print_exc(file=f)
    print("CRASHED or EXITED!")
    sys.exit(1)
