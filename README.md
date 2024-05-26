# Spiker Playback

Music playback control using SpikerBox.

## Project Structure

There are two main files in the root directory,

- `analysis.ipynb` contains code for the analysis that helps reach the final
  model, and
- `app.py` contains code for the GUI and final model running in real time

The `data` directory contains the original CSV files from the labs. They are
labelled in weeks.

## Deployment

If you don't have [pipenv], follow the official instruction.

Then, simply run the following command to install all the dependencies in a new
environment,

```
pipenv install
```

Then, you can start the application with `python app.py`.

## Development

_If you want to run the notebook, you need the development dependencies._

Simply run the following command to install all the dependencies in a new
environment for development,

```
pipenv install --dev
```

### Optional pre-commit hooks

Install pre-commit git hooks to clean and solve merge conflicts for Jupyter
Notebooks.

```
pip install pre-commit
pre-commit install
```

About [nbdev clean],

> To avoid pointless conflicts while working with jupyter notebooks (with
> different execution counts or cell metadata), it is recommended to clean the
> notebooks before committing anything (done automatically if you install the
> git hooks with nbdev_install_hooks).

About [nbdev merge],

> When working with jupyter notebooks (which are json files behind the scenes)
> and GitHub, it is very common that a merge conflict (that will add new lines
> in the notebook source file) will break some notebooks you are working on.

[pipenv]: https://pipenv.pypa.io/en/latest/
[nbdev clean]: https://nbdev.fast.ai/api/clean.html
[nbdev merge]: https://nbdev.fast.ai/api/merge.html
