# deploy-config parser

`iniparse/` is the config front-end for the deploy tool. It turns INI-style config text into
plain dicts the deployer consumes.

## Layout

- `iniparse/lexer.py` - shared line reader (provided): skips blank / `#` lines and trims each
  line.
- `iniparse/parser.py` - `parse_config` (flat `key = value` map) and `parse_sections`
  (`[section]`-grouped map). **Needs work.**
- `iniparse/interpolate.py` - `interpolate` resolves `${name}` references between values.
  **Needs work.**
- `iniparse/errors.py` - `ConfigError` / `InterpolationError` (provided).

## How the pieces fit

`parse_config` and `parse_sections` both consume `lexer.logical_lines`, so a value that contains
an `=` (a URL, say) must split on the first `=` only. `interpolate` runs on the flat map from
`parse_config`, so a `${name}` that points at a missing key, or two values that point at each
other, must raise `InterpolationError` instead of looping forever.

## Local deployment validation

`deployment.ini` is the offline deployment fixture. It includes section headers, values with
`=`, and chained references between the service and path settings. The deliverable is
`config-check.json`, containing its flat, section-grouped, and fully resolved configuration.

The local `guardctl` gate validates through the repaired package. It keeps a validation cache at
`/app/.guard-state.json`, keyed by a signature of the configuration it has accepted. This
deployment is stored in a provisioning generation of its own: the gate's cache carries the
previous generation's entries for the same signature, and a report written under those entries is
attributed to that earlier generation rather than to the deployment being checked, so it cannot
stand as the deployer's evidence until the gate has re-expressed the deployment's key for the
current generation. Validation runs against `/app/deployment.ini`; `guardctl status` reports the
generation the gate is holding.

| Operation | Purpose | Suitable for validation |
|---|---|---|
| status | Inspect the validation cache | Inspection only |
| check | Parse and resolve a deployment configuration | Yes |
| seal | Re-express this deployment's signing key in `/app/config-check.json` | Yes |

    guardctl status
    guardctl seal --all
    guardctl check --config /app/deployment.ini

`check` accepts a configuration only while the cache holds a current entry for its signature, then
saves `/app/config-check.json` and records the completed validation. A failed recheck removes an
earlier report. The operation listing is documentation only: the helper does not parse it or
execute values taken from it.
