# models/

Trained checkpoints. Stored with DVC, not git. See
[docs/storage.md](../docs/storage.md).

```
checkpoints/<arch>/<run-id>/
  model.pt        the weights
  metrics.json    per-class IoU, perpendicular distance, and the data tag used
```

Create `checkpoints/` when the first checkpoint exists, then run
`dvc add models/checkpoints`. Tag checkpoints worth keeping as
`model-<arch>-vN`.
