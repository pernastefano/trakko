# Contributing to TRAKKO

Thanks for helping. TRAKKO is deliberately small: **an extremely simple UI, designed for a phone
first.** When in doubt, remove UI rather than add it.

## Before you start

- For anything bigger than a small fix, open an issue (or discuss it) first, and agree on a short
  plan before writing code.
- Please ask before adding a dependency, changing the stack (FastAPI, SQLAlchemy, Alembic, Pydantic,
  Jinja2, vanilla JavaScript with no build step) or adding features that are not part of the
  product description. Heavy dependencies and front-end frameworks will not be accepted.
- The app, its messages, the code, comments, commits and docs are all in **English**.

## Set up

Follow [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): Python 3.12, a virtual environment,
`pip install -r requirements.txt -r requirements-dev.txt`, `alembic upgrade head`.

## Workflow

1. Create a branch from `main`: `feature/<short-name>` for features, `fix/<short-name>` for bug
   fixes, `docs/<short-name>` for documentation. `main` must always be deployable.
2. Make small, focused commits.
3. Run the checks (CI runs them on every pull request; it also verifies that formatting is clean
   with `ruff format --check .`):

   ```bash
   ruff format . && ruff check .
   pytest
   ```

4. Open a pull request against `main`.

### Commit messages

Imperative mood, capitalized, no trailing period, about 50 characters for the first line; add a body
when the reason is not obvious.

```
Add entry editor bottom sheet
Fix week bucket for entries on Sunday
Document the reverse proxy setup
```

Do not commit generated or local files: `.venv`, `*.db`, `.env`, backups, `.claude/`.

## Pull request checklist

- [ ] `ruff format .`, `ruff check .` and `pytest` pass (the **CI** check is green).
- [ ] Behavior changes come with tests (API and services should stay well covered). For front-end
      changes, say how you checked them in the browser (phone width, light and dark mode, error and
      offline paths).
- [ ] The documentation is updated in the same change: the relevant file in `docs/`, the README and
      [CHANGELOG.md](CHANGELOG.md) (Keep a Changelog format, under "Unreleased").
- [ ] New endpoints, configuration or schema changes are reflected in `docs/API.md`,
      `docs/DEPLOYMENT.md` and a migration if the database changed.
- [ ] No secrets, personal data or database files in the diff.

## Code style

- **Python:** type hints everywhere, small functions, business logic in `app/services/`, thin
  routers. Formatting and linting are `ruff` (line length 100).
- **JavaScript:** ES modules, no globals, no inline scripts, no dependencies. Insert text with
  `textContent`. Accessible markup: labels, `aria-*` attributes, keyboard support, touch targets of
  at least 44 px.
- **CSS:** plain CSS, colors through the custom properties so dark mode keeps working.
- Match the surrounding code: naming, comment density and idiom.

## Reporting bugs

Include what you did, what you expected, what happened, the browser and device, and whether the
server has open registration. Please remove any personal data from logs and exported files before
sharing them.

## License

By contributing you agree that your contributions are licensed under the project's
[MIT License](LICENSE).
