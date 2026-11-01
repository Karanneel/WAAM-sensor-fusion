"""Run model-error, dropout and generator-sensitivity experiments together."""

import json
import platform
from pathlib import Path
from dataclasses import asdict
import importlib.metadata
import hashlib
import time
from learned import train_models, TRAIN_SEEDS, TRAIN_DWELLS
from sweep import run_sweep
from evaluation import evaluate_gate, tied_winners
from plot_crossover import plot_crossover
from process import sample_build_parameters

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'reports'/'experiments'
METRICS = [('wall_err','Final height error (mm)'), ('rmse_H','Height RMSE (mm)'),
           ('rmse_s','Standoff RMSE (mm)'), ('rmse_T','Temperature RMSE (C)')]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    print('Training sensor and schedule-only models on seeds 100-149.', flush=True)
    models = train_models()
    schedule_models = train_models(subset=set())
    results = {}
    for name, options in [('model_error', {}), ('dropout', {'dropout_p': .20}),
                          ('generator_variant', {'variant': True})]:
        print(f'Running {name}...', flush=True)
        frame = run_sweep(models, schedule_models, **options)
        frame.to_csv(OUT/f'{name}.csv', index=False)
        results[name] = frame
        for metric, label in METRICS:
            plot_crossover(frame, metric, label, OUT/f'{name}_{metric}.png')
    # A dwell condition that is absent from training, with independent build seeds.
    print('Running unseen 90 s dwell condition...', flush=True)
    results['unseen_dwell'] = run_sweep(models, schedule_models, error_types=('width_temperature',),
                                       levels=(0.0,), gains=(1.0,), dwell=90)
    results['unseen_dwell'].to_csv(OUT/'unseen_dwell.csv', index=False)
    gate = evaluate_gate(results['model_error'], results['dropout'])
    gate.to_csv(OUT/'paired_improvements.csv', index=False)
    sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted((ROOT/'src').glob('*.py'))}
    manifest = dict(protocol='2026-11-01 revision', training_seeds=list(TRAIN_SEEDS),
                    training_dwells=list(TRAIN_DWELLS), evaluation_seeds=list(range(30)),
                    n_layers=31, dropout_probabilities=[.02,.20],
                    physical_variation='independent uniform +/-5% width, slope, heat and cooling parameters',
                    generator_variant=dict(shape=.75, cooling_exponent=.85, ctwd_bias_mm=.5,
                                           status='previously inspected sensitivity condition'),
                    nominal_parameters=asdict(sample_build_parameters(0, varied=False)),
                    python=platform.python_version(),
                    packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','matplotlib']},
                    source_sha256=sources, seconds=round(time.time()-started, 2))
    (OUT/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    write_summary(results, gate)
    print(f'Wrote results to {OUT} in {manifest["seconds"]} s.', flush=True)


def write_summary(results, gate):
    lines = ['# Estimator comparison', '',
             'Generated with the revised 2026-11-01 protocol. Errors below are means across 30 independent test builds.',
             'These are simulation results. They do not validate a WAAM cell or establish an optimal estimator.', '',
             '| Condition | Estimator | Final height error (mm) | H RMSE (mm) | S RMSE (mm) | T RMSE (C) |',
             '|---|---|---:|---:|---:|---:|']
    for name, frame in results.items():
        base=frame[(frame.error_type=='width_temperature')&(frame.level==0)&(frame.gain==1)]
        for estimator, values in base.groupby('estimator'):
            means=values[['wall_err','rmse_H','rmse_s','rmse_T']].mean()
            lines.append(f'| {name} | {estimator} | '+ ' | '.join(f'{v:.4f}' for v in means)+' |')
    lines += ['', '## Paired improvement check', '',
              'The three categories are layer-end standoff, drifted temperature, and dropout-only joint height/standoff error.',
              'For each error type, gain and zero/low error level, a category passes with at least 10% lower mean build RMSE and a paired-bootstrap 95% interval for improvement above zero.',
              'Each category requires 30 valid paired builds. The first layer is excluded from dropout scoring.', '']
    cell_scores=gate.groupby(['estimator','error_type','level','gain']).passed.sum()
    for estimator in ['EKF','learned']:
        counts=cell_scores.loc[estimator]
        lines.append(f'- {estimator}: at least two categories pass in {int((counts>=2).sum())}/{len(counts)} conditions.')
    lines += ['', 'This check replaces the earlier, unsupported pass statement; it does not retroactively validate the original protocol.', '',
              '## Generator sensitivity', '',
              'The variant was inspected before this revision and is not an unseen validation set. Near-equal point estimates are treated as ties within 1e-6; no significance is inferred from a winner label.', '']
    for metric,_ in METRICS:
        main=tied_winners(results['model_error'],metric)
        other=tied_winners(results['generator_variant'],metric)
        matches=sum(main[k]==other[k] for k in main)
        lines.append(f'- {metric}: matching minimum-mean estimator sets in {matches}/{len(main)} conditions.')
    (OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
