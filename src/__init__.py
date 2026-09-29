"""Application package bootstrap configuration."""

import os


# The embedding stack uses PyTorch.  Set backend selection as soon as the
# package is entered (before modules such as agents can import Transformers).
# USE_TORCH also removes ambiguity in Transformers installations that contain
# an incompatible optional TensorFlow/tf-keras combination.
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TF"] = "1"
