# imap2rtm

Simple Python tool which transfers emails from multiple mailboxes to one inbox in [Remembet the milk (RTM)](https://www.rememberthemilk.com/).

## Purpose of this tool

If you are interested in time management, you probably heard about [Getting things done (GTD)](https://www.amazon.com/Getting-Things-Done-Stress-Free-Productivity/dp/0143126563). GTD is a productivity framework which teaches you how to organize your tasks, keep track of important things and be happy and productive.

In the book, you learn about Inbox which should be some incoming queue for new tasks and ideas which should be considered later. The problem is that in the modern world you have probably more than one Inbox which makes it harder.

This tool allows me to transfer important messages from my email accounts to a single Inbox in RTM.

## Installation

If you want to use it, you'll need Python 3.6 or higher and IMAPClient library. You can install IMAPClient to a virtual environment from PyPI via `pip install IMAPClient`.

## Configuration

Email accounts can be configured in `config.ini` file. Take a look there and you'll understand what should be where.

Unfortunately, the behavior of this tool cannot be configured via any kind of configuration so if you want to use it, you can eighter adapt my workflow or fork/adjust the `imap2rtm.py` script to fit your needs.

## My workflow

Usually, I process my emails/task in this way:

1. Read all new emails in Thunderbird and mark them with flags:

    * Red flag - for emails which should be transferred to RTM as important tasks
    * Blue flag - for emails which should be also transferred and I need to keep them here to not forget to reply to them
    * Yellow flag - for email which should be transferred but I can forget about (for example notifications from Github)

1. Run this tool, which does these steps:

    * Finds all emails marked by flags mentioned above.
    * Adjusts email subjects, takes plain text body or HTML without tags.
    * Sends them via SMTP to RTM.
    * Sets green or no flag to original emails via IMAP.

1. Go to RTM Inbox and set priority, due date etc. to each task and move them to appropriate list.

## Adaptation

If you don't want to adapt my workflow, feel free to fork this repository and adapt the `imap2rtm.py` script as you need.

## License

MIT