# Reproducing PLAB

## Setup

```bash
git clone https://github.com/NidhiMehta/plab.git
cd plab
pip install -r requirements.txt
cp .env.example .env   # fill in H2OGPTE_API_KEY and H2OGPTE_ADDRESS
```

## Run v0.3 (3,600 cases)

```bash
# Generate corpus (one-time)
python -m src.generator --output data/v0.3/cases.jsonl

# 144-case pilot (1 case per attack × domain × difficulty)
./scripts/run_pilot.sh

# Full 3,600-case run
./scripts/run_pilot.sh --full

# Options
./scripts/run_pilot.sh --cells 2         # 288 cases
./scripts/run_pilot.sh --limit 20        # quick smoke test
./scripts/run_pilot.sh --concurrency 8   # more parallelism
./scripts/run_pilot.sh --skip-generate   # skip corpus regen
```

Results land in `results/v0.3/<timestamp>.jsonl`.

### Score

```bash
python -m src.scorer \
  --input results/v0.3/<timestamp>.jsonl \
  --output results/v0.3/<timestamp>_summary.json
```

### Report

```bash
python scripts/make_report.py \
  --input results/v0.3/<timestamp>.jsonl \
  --output results/v0.3/report.html
```

## Run v0.4 (45 cases, 5 models)

```bash
python -m src.evaluator_v04 \
  --cases schema/case.v0.4.cases.jsonl \
  --model claude-opus-4-7 \
  --output results/v0.4/full_run/claude-opus-4-7.jsonl
```

Repeat for each model (`gpt-5`, `gemini-2.5-pro`, `o3`, `deepseek-r1`).

### Comparison report

```bash
python scripts/make_v04_report.py \
  --input-dir results/v0.4/full_run/ \
  --output results/v0.4/full_run/comparison_report.html
```

## Regenerate figures

```bash
python paper/figures/gen_figures.py
# Convert to PDF for LaTeX (requires librsvg):
for f in paper/figures/fig*.svg; do
  rsvg-convert -f pdf -o "${f%.svg}.pdf" "$f"
done
```

## Compile paper

```bash
# Requires tectonic (https://tectonic-typesetting.github.io)
cd paper && tectonic main.tex
```

## Tests

```bash
pytest tests/
```
