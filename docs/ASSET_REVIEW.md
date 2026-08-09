# Asset review and rollback

Kizuna keeps every generated character sheet, background, and storyboard version. The Compositor's Asset Review board is the production gate for deciding which version should feed shots.

## Review states

- **Pending** is the default for newly generated assets.
- **Approve alternate** records approval without changing the current production version.
- **Use this version** approves the asset and makes it the active production version for its character, location, or shot.
- **Reject** records that the version should not be used. Notes stay attached to that exact version.

Only one version in a group can be the explicitly selected production master. If no version has been selected, Kizuna prefers the newest approved version and then the newest version that has not been rejected.

## What changes when a version is selected

New shot compositions and Timeline stills use the selected asset. Existing composition layers linked to another version in the same group are relinked to the selected version. Each affected composition receives a new version number and its old rendered preview is marked stale, so the next render cannot be mistaken for the newly approved picture.

Selecting an older version is a rollback, but it never deletes newer files, review records, or history. The creator can return to any retained version later.
