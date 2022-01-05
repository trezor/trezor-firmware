# Updating pyright

1. Update the version number in `package.json`.

2. Run `./generate-dependencies.sh`. The script uses [node2nix](https://github.com/svanderburg/node2nix)
   to resolve dependencies and save their hashes to `node-packages.nix`.

3. (optional) Check that the package builds by spawning nix-shell in top-level of the repo:
   ```
   cd ../..
   nix-shell
   ```
   Or check that it builds with your local nixpkgs:
   ```
   nix-build -E "(import <nixpkgs> {}).callPackage ./default.nix {}"
   ```

4. Commit `.nix` files generated in step 2 to git:
   ```
   git add package.json *.nix
   ```
