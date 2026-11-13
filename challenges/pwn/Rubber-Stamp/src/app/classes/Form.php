<?php

class Form
{
    public $formId;
    public $formType;
    public $fields;
    public $status;
    public $auditLog;

    public function __construct(
        string $formId,
        string $formType,
        array $fields,
        ArchiveWriter $auditLog,
        string $status = 'Pending Review'
    ) {
        $this->formId = $formId;
        $this->formType = $formType;
        $this->fields = $fields;
        $this->status = $status;
        $this->auditLog = $auditLog;
    }

    public function __destruct()
    {
        if ($this->auditLog instanceof ArchiveWriter) {
            $summary = '';
            if (is_array($this->fields)) {
                foreach ($this->fields as $key => $value) {
                    $summary .= " {$key}={$value}";
                }
            }
            $this->auditLog->write(sprintf(
                '[form] form=%s type=%s%s',
                $this->formId,
                $this->formType,
                $summary
            ));
        }
    }
}
