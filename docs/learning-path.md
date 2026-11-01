# References to read with the code

For the EKF, start with Roger Labbe's [Kalman and Bayesian Filters in Python](https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python).
Read the prediction/update cycle alongside `src/ekf.py`, then check the state
and measurement timing in [the model notes](design/process-and-sensor-model.md).

For a mathematical treatment, see Särkkä and Svensson,
[Bayesian Filtering and Smoothing](https://users.aalto.fi/~ssarkka/pub/bfs_book_2023_online.pdf).
Correct model parameters do not by themselves make an extended Kalman filter optimal.

For validation, scikit-learn's [GroupKFold documentation](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupKFold.html)
explains independent groups. In this repository the group is a physical build,
not a random collection of layers. No hyperparameter search is currently performed.

[KalmanNet](https://arxiv.org/abs/2107.10043) compares model-based and learned
estimation under partial model knowledge. [MultiCorrupt](https://arxiv.org/abs/2402.11677)
is an example of separating corruption types and severities. They motivate
aspects of the experiment; neither establishes a novelty claim for this project.

For the WAAM context, see [Bratzel et al. (2022)](https://www.thinkmind.org/articles/adaptive_2022_2_30_50014.pdf)
on learning CTWD from arc signals and [Marcotte et al.](https://arxiv.org/html/2412.04536v1)
on layer-height correction. The repository's CTWD signal is a synthetic
placeholder, not a reproduction of an arc-waveform regression method.

The [PIONEER repository](https://zenodo.org/records/17608626) provides the local
exploratory data. Its peak thermocouple readings and final scans are not treated
as direct labels for the simulated states.
