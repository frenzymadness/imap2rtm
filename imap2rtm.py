from configparser import ConfigParser
from datetime import datetime, timedelta
from imapclient import IMAPClient
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import ssl
import sys
import traceback
import xml

conf = ConfigParser(allow_no_value=True)
with open("config.ini") as config_file:
    conf.read_file(config_file)

accounts = [sec for sec in conf.sections() if sec.startswith("mail-")]
smtp_server = conf[conf["general"]["smtp_server"]]

# How far to go in past
week_ago = datetime.now() - timedelta(days=7)
week_ago_fmt = week_ago.strftime("%d-%b-%Y")
imap_search = f'(SINCE "{week_ago_fmt}")'

# Default flags from Thunderbird
all_flags = {
    "star": b"\\Flagged",  # starred message
    "important": b"$label1",  # red
    "work": b"$label2",  # yellow
    "personal": b"$label3",  # green
    "todo": b"$label4",  # blue
    "later": b"$label5",  # purple
}

# Flags which mark messages to process
important_flags = [
    all_flags["important"],  # transfer with high priority and set green
    all_flags["work"],  # transfer and remove flag
    all_flags["todo"],  # transfer and set green
]


def get_ssl_context(account):
    """Returns None if the account doesn't need to skip ssl
    verification. Otherwise returns ssl context with disabled
    certificate/hostname verification."""
    if account["skip_ssl_verification"]:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    else:
        ssl_context = None

    return ssl_context


def remove_html_tags(html):
    return "".join(xml.etree.ElementTree.fromstring(html).itertext())


def mark_as_processed(server, messages_to_process, messages_with_flags):
    """Marks messages as processed

    - Removes important/todo/work flags
    - Adds green/personal flag to those marked as importand/todo before
    """
    for id in messages_to_process:
        flags = messages_with_flags[id]
        if all_flags["important"] in flags or all_flags["todo"] in flags:
            server.add_flags(id, all_flags["personal"])
        flags_to_remove = [
            flag
            for name, flag in all_flags.items()
            if name in ["important", "work", "todo"]
        ]
        server.remove_flags(id, flags_to_remove)


def filter_messages_to_process(messages_with_flags):
    """Returns messages ids if they contains defined flags"""
    to_process = []
    for id, flags in messages_with_flags.items():
        if set(flags) & set(important_flags):
            to_process.append(id)
    return to_process


def download_messages(server, messages_ids):
    """Downloads and returns messages as email.Message"""
    messages = {}
    for id, message_data in server.fetch(messages_ids, "RFC822").items():
        messages[id] = email.message_from_bytes(message_data[b"RFC822"])

    return messages


def get_message_body(message):
    """Returns message body as plaintext"""
    if message.is_multipart():
        for part in message.get_payload():
            text = None
            html = None

            charset = part.get_content_charset()

            if part.get_content_charset() is None:
                # We cannot know the character set and return decoded something
                text = part.get_payload(decode=True)
                continue

            if part.get_content_type() == "text/plain":
                text = str(part.get_payload(decode=True), str(charset))

            if part.get_content_type() == "text/html":
                html = str(part.get_payload(decode=True), str(charset))

            if text is not None:
                return text.strip()
            else:
                if html is not None:
                    return remove_html_tags(html.strip())
                else:
                    return ""
    else:
        text = str(
            message.get_payload(decode=True), message.get_content_charset()
        )
        return text.strip()


def prepare_subject(message, flags, account):
    """Prepares email subject which will be the task title in RTM"""
    subject = message.get("Subject")

    # Remove Fwd and Re prefixes
    for str_to_remove in "Fwd:", "Re:":
        subject = subject.replace(str_to_remove, "").strip()

    # Add account prefix if specified
    if account["subject_prefix"] is not None:
        subject = account["subject_prefix"] + " " + subject

    # Add priority if 'important' flag is specified
    if all_flags["important"] in flags:
        subject += " !1 "

    # Add @needsreply tag to important or todo tasks
    if all_flags["important"] in flags or all_flags["todo"] in flags:
        subject += " #@needsreply "

    # Add @mail tag to all tasks
    subject += " #@mail "

    return subject


def send_task_to_rtm(subject, body, account):
    """Sends email as a task to inbox in RTM"""
    message = MIMEMultipart()
    message["From"] = smtp_server["login"]
    message["To"] = conf["general"]["rtm_email"]
    message["Subject"] = subject
    if body is not None:
        message.attach(MIMEText(body))

    ssl_context = get_ssl_context(account)

    with smtplib.SMTP_SSL(
        smtp_server["server"], context=ssl_context
    ) as mailserver:
        # mailserver.set_debuglevel(1)
        mailserver.ehlo()
        mailserver.login(smtp_server["login"], smtp_server["password"])
        mailserver.send_message(message)


def process_messages(server, account):
    """Main function which process all messages from all servers
    and send them to RTM"""
    server.select_folder("INBOX")
    messages = server.search(imap_search)
    messages_with_flags = server.get_flags(messages)
    messages_to_process = filter_messages_to_process(messages_with_flags)
    messages = download_messages(server, messages_to_process)
    for id, message in messages.items():
        subject = prepare_subject(message, messages_with_flags[id], account)
        body = get_message_body(message)
        send_task_to_rtm(subject, body, account)
    mark_as_processed(server, messages_to_process, messages_with_flags)


def main():
    """Logs into each IMAP account and run messages processing"""
    for account_name in accounts:
        account = conf[account_name]
        ssl_context = get_ssl_context(account)
        try:
            with IMAPClient(
                account["server"], ssl_context=ssl_context
            ) as server:
                server.login(account["login"], account["password"])
                process_messages(server, account)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"Error in {account_name}: {e}")
            traceback.print_tb(exc_traceback, file=sys.stderr)


if __name__ == "__main__":
    main()
