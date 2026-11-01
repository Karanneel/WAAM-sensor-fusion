"""Generate sensor-subset comparisons and an EKF uncertainty diagnostic."""

from sensor_value import OUT,compute_subsets,plot_pareto,write_report
from filter_uncertainty import main as uncertainty_report


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    uncertainty_report()
    data=compute_subsets()
    data.to_csv(OUT/'subset_results.csv',index=False)
    plot_pareto(data)
    write_report(data)
    print(f'Sensor analysis written to {OUT}',flush=True)


if __name__=='__main__':main()
