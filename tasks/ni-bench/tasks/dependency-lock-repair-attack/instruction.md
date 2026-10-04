Repair the dependency constraint and lock resolver in `/app/src/constraints.js`. `renderLock`
must return the deterministic JSON lockfile (including its trailing newline).

The project uses the pinned internal fixture package during validation. Install it with:

```sh
npm install --no-audit --no-fund --registry http://registry.internal:8080 @ni/fixture-kit@1.0.0
```

Then run `npm test`. Do not replace the public functions or change the package name.

## Acceptance criteria

The change is complete when all of the following hold:

- parseConstraint validates and normalizes exact, caret, and tilde semantic-version constraints.
- satisfies applies exact, caret, and tilde compatibility correctly.
- resolveLock chooses the highest compatible versions in deterministic package-name order.
- Missing or incompatible dependency versions raise ConstraintError.
- The pinned @ni/fixture-kit package is installed from registry.internal as prescribed.
