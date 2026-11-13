from pathlib import Path
import shutil
import subprocess
import tempfile
import yaml


challenge_directory = Path(__file__).resolve().parent.parent
with (challenge_directory / 'challenge.yml').open() as metadata_file:
    flag = yaml.safe_load(metadata_file)['flags'][0]
overrideKey = flag[5:-1]

archiver = shutil.which('7z')
if archiver is None:
    raise RuntimeError('Install 7-Zip (7z) to build the encrypted navigation log')

# Build a fresh archive so old entries cannot remain in the distributed ZIP.
with tempfile.TemporaryDirectory() as temporary_directory:
    archive_path = Path(temporary_directory) / 'navigation_log.zip'
    result = subprocess.run(
        [archiver, 'a', '-tzip', '-mem=AES256', f'-p{overrideKey}',
         str(archive_path), 'navigation_log.txt'],
        cwd=challenge_directory / 'src',
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError('Could not encrypt the navigation log')
    shutil.copyfile(archive_path, challenge_directory / 'dist/navigation_log.zip')

print('Saved encrypted navigation log to dist/navigation_log.zip')
