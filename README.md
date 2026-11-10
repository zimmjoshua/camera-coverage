# Hardware camera coverage

A software camera picks a hardware camera for each shot. A hardware camera can take that shot only when the subject distance and the light level are both inside its supported ranges. `cameras_suffice` reports whether the hardware cameras cover every combination in the required distance range and light range.

Ranges are closed: a camera that supports distances 0 through 5 and a camera that supports 5 through 10 together cover distance 5. Covering the two axes independently is not the same as covering the rectangle. The implementation sweeps across distance and checks that the active light ranges cover the required light range at every point.

The solution is the standard-library file `cameras.py`. No third-party packages are used.

```bash
python3 cameras.py
```
