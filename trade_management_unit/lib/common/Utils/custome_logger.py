# custom_logger.py
import logging
import logging.handlers
import queue
import inspect
import threading
import traceback

# Create a queue for the log messages
log_queue = queue.Queue(-1)

# Create a handler that sends log messages to the queue
queue_handler = logging.handlers.QueueHandler(log_queue)

# Create a listener that receives log messages from the queue and sends them to the desired handler
file_handler = logging.FileHandler('/Users/nareshjoshi/Documents/personal_workspace/ats_aplication/logfile.log')

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

listener = logging.handlers.QueueListener(log_queue, file_handler)

# Start the listener
listener.start()



def log(message,level="info"):
    # Get the record of the caller
    caller = inspect.getframeinfo(inspect.stack()[1][0])

    # Create a logger
    logger = logging.getLogger(__name__)

    # Check if the logger has handlers
    if not logger.handlers:
        # Add the queue handler to the logger
        logger.addHandler(queue_handler)

    # Get the current thread ID
    thread_id = threading.get_ident()

    # Get the current thread name
    thread_name = threading.current_thread().name

    # Log the message along with the file and line number of the caller, the thread ID, and the thread name
    if level == 'error':
        stack_trace = traceback.format_stack()
        logger.error(f'ThreadID: {thread_id}, ThreadName:  {thread_name}  - - {message}, StackTrace: {stack_trace}')
    else:
        logger.info(f'ThreadID: {thread_id}, ThreadName:  {thread_name}  - - {message}')


    # Remove the handler after use to prevent duplicate logs
    logger.removeHandler(queue_handler)



