# always use a VCS kids

**Category:** Forensics  
**Difficulty:** Medium  
**Author:** Grace  

## Description

You found a suspicious git repository in the servers of the ship. See if you can find anything
interesting in there.

## Files Provided

- `my_calculator.tar.gz`

## Flag

`flag{d0-y0u-kn0w-4b0u7-git-reflog?}`

## Solution

If you **run `git fsck --lost-found`** in the repository, you'll see a few dangling commits. In one
of the dangling commits, there will be a file in the commit that contains the flag.

We can use `git grep` so that we don't have to manually `git checkout` every dangling commit and
then grep.

## Solve Script

See `solution/solve.sh` for the full command to automatically find the flag.

## Techniques / Tags

`git`

## Setup / Deployment Notes

N/A

## Known Issues / Notes

N/A
