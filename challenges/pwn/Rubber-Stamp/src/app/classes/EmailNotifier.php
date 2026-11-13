<?php

class EmailNotifier
{
    private const ALLOWED_RECIPIENTS = ['finance@razorpowerco.sys', 'logistics@razorpowerco.sys'];

    public $recipient;
    public $subject;

    public function __wakeup()
    {
        if (!in_array($this->recipient, self::ALLOWED_RECIPIENTS, true)) {
            $this->recipient = 'finance@razorpowerco.sys';
        }
    }

    public function __destruct()
    {
        file_put_contents('/var/log/rubberstamp/mail.log', sprintf(
            '[mail] to=%s subject=%s%s',
            $this->recipient,
            $this->subject,
            PHP_EOL
        ), FILE_APPEND);
    }
}
