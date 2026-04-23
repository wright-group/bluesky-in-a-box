from bluesky.plans import count
from bluesky.preprocessors import baseline_decorator

# Wrap all of the plans with baseline which reads movables before and after
# count = baseline_decorator(movables)(count)
