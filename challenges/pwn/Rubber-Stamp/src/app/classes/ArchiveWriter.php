<?php

class ArchiveWriter
{
    public $archivePath;

    public function __construct(string $archivePath)
    {
        $this->archivePath = $archivePath;
    }

    public function write(string $entry): void
    {
        file_put_contents($this->archivePath, $entry . PHP_EOL, FILE_APPEND);
    }
}
