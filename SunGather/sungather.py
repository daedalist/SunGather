#!/usr/bin/python3

from SungrowClient import SungrowClient
from version import __version__

import importlib
import logging
import logging.handlers
import sys
import getopt
import yaml
import time
import signal
import traceback


def print_help():
    """Print help message for command line usage."""
    print(f'\nSunGather {__version__}')
    print(f'\nhttps://sungather.app')
    print(f'usage: python3 sungather.py [options]')
    print(f'\nCommandling arguments override any config file settings')
    print(f'Options and arguments:')
    print(f'-c config.yaml             : Specify config file.')
    print(f'-r registers-file.yaml     : Specify registers file.')
    print(f'-l /logs/                  : Specify folder to store logs.')
    print(f'-v 30                      : Logging Level, 10 = Debug, 20 = Info, 30 = Warning (default), 40 = Error')
    print(f'--runonce                  : Run once then exit')
    print(f'-h                         : print this help message and exit (also --help)')
    print(f'\nExample:')
    print(f'python3 sungather.py -c /full/path/config.yaml\n')


def load_config(filename):
    """Load and parse configuration YAML file.

    Args:
        filename: Path to config.yaml file

    Returns:
        dict: Parsed configuration content

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is invalid or missing required fields
    """
    try:
        with open(filename, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {filename}")
    except yaml.YAMLError as err:
        raise ValueError(f"Invalid YAML in config file {filename}: {err}")
    except Exception as err:
        raise ValueError(f"Failed loading config {filename}: {err}")

    if not config:
        raise ValueError(f"Config file {filename} is empty")

    if not config.get('inverter'):
        raise ValueError("Config file missing required 'inverter' section")

    return config


def load_registers(filename):
    """Load and parse registers YAML file.

    Args:
        filename: Path to registers file

    Returns:
        dict: Parsed registers content

    Raises:
        FileNotFoundError: If registers file doesn't exist
        ValueError: If registers file is invalid
    """
    try:
        with open(filename, encoding="utf-8") as f:
            registers = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Registers file not found: {filename}")
    except yaml.YAMLError as err:
        raise ValueError(f"Invalid YAML in registers file {filename}: {err}")
    except Exception as err:
        raise ValueError(f"Failed loading registers {filename}: {err}")

    if not registers:
        raise ValueError(f"Registers file {filename} is empty")

    return registers


def build_inverter_config(config_dict):
    """Build inverter configuration from parsed config file.

    Args:
        config_dict: Parsed config.yaml content

    Returns:
        dict: Inverter configuration with defaults applied

    Raises:
        ValueError: If inverter section is missing or invalid
    """
    if 'inverter' not in config_dict:
        raise ValueError("Config missing 'inverter' section")

    inverter = config_dict['inverter']
    if inverter is None:
        inverter = {}

    return {
        "host": inverter.get('host', None),
        "port": inverter.get('port', 502),
        "timeout": inverter.get('timeout', 10),
        "retries": inverter.get('retries', 3),
        "slave": inverter.get('slave', 0x01),
        "scan_interval": inverter.get('scan_interval', 30),
        "connection": inverter.get('connection', "modbus"),
        "model": inverter.get('model', None),
        "smart_meter": inverter.get('smart_meter', False),
        "use_local_time": inverter.get('use_local_time', False),
        "log_console": inverter.get('log_console', 'WARNING'),
        "log_file": inverter.get('log_file', 'OFF'),
        "level": inverter.get('level', 1)
    }


def parse_arguments(argv=None):
    """Parse command line arguments.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        dict: Parsed arguments with keys:
            - config_file: Path to config file
            - registers_file: Path to registers file
            - log_folder: Path to log folder
            - log_level: Optional logging level (10-50)
            - run_once: Boolean flag for single run mode
            - show_help: Boolean flag indicating help was requested

    Raises:
        getopt.GetoptError: If argument parsing fails
        ValueError: If argument validation fails
    """
    if argv is None:
        argv = sys.argv[1:]

    # Default values
    result = {
        'config_file': 'config.yaml',
        'registers_file': 'registers-sungrow.yaml',
        'log_folder': '',
        'log_level': None,
        'run_once': False,
        'show_help': False
    }

    # Parse arguments - let getopt.GetoptError propagate
    opts, args = getopt.getopt(argv, "hc:r:l:v:", "runonce")

    for opt, arg in opts:
        if opt == '-h':
            result['show_help'] = True
            return result
        elif opt == '-c':
            result['config_file'] = arg
        elif opt == '-r':
            result['registers_file'] = arg
        elif opt == '-l':
            result['log_folder'] = arg
        elif opt == '-v':
            if not arg.isnumeric():
                raise ValueError(
                    f"Invalid log level '{arg}'. Valid options: 10 = Debug, 20 = Info, 30 = Warning (default), 40 = Error"
                )
            level = int(arg)
            if level < 0 or level > 50:
                raise ValueError(
                    f"Log level {level} out of range. Valid options: 10 = Debug, 20 = Info, 30 = Warning (default), 40 = Error"
                )
            result['log_level'] = level
        elif opt == '--runonce':
            result['run_once'] = True

    return result


def main():
    # Parse command line arguments
    try:
        args = parse_arguments()
    except getopt.GetoptError as e:
        logging.error(f'Invalid command line arguments: {e}')
        sys.exit(2)
    except ValueError as e:
        logging.error(str(e))
        sys.exit(2)

    # Handle help request
    if args['show_help']:
        print_help()
        sys.exit(0)

    # Extract arguments
    configfilename = args['config_file']
    registersfilename = args['registers_file']
    logfolder = args['log_folder']
    loglevel = args['log_level']
    runonce = args['run_once']

    logging.info(f'Starting SunGather {__version__}')
    logging.info(f'Need Help? https://github.com/bohdan-s/SunGather')
    logging.info(f'NEW HomeAssistant Add-on: https://github.com/bohdan-s/hassio-repository')

    # Load configuration files
    try:
        configfile = load_config(configfilename)
        logging.info(f"Loaded config: {configfilename}")
    except (FileNotFoundError, ValueError) as err:
        logging.error(f"Failed loading config: {err}")
        sys.exit(1)

    try:
        registersfile = load_registers(registersfilename)
        logging.info(f"Loaded registers: {registersfilename}")
        logging.info(f"Registers file version: {registersfile.get('version','UNKNOWN')}")
    except (FileNotFoundError, ValueError) as err:
        logging.error(f"Failed loading registers: {err}")
        sys.exit(1)

    # Build inverter configuration
    try:
        config_inverter = build_inverter_config(configfile)
    except ValueError as err:
        logging.error(f"Invalid inverter configuration: {err}")
        sys.exit(1)

    if loglevel is not None:
        logger.handlers[0].setLevel(loglevel)
    else:
        logger.handlers[0].setLevel(config_inverter['log_console'])

    if not config_inverter['log_file'] == "OFF":
        if config_inverter['log_file'] == "DEBUG" or config_inverter['log_file'] == "INFO" or config_inverter['log_file'] == "WARNING" or config_inverter['log_file'] == "ERROR":
            logfile = logfolder + "SunGather.log"
            fh = logging.handlers.RotatingFileHandler(logfile, mode='w', encoding='utf-8', maxBytes=10485760, backupCount=10) # Log 10mb files, 10 x files = 100mb
            fh.formatter = logger.handlers[0].formatter
            fh.setLevel(config_inverter['log_file'])
            logger.addHandler(fh)
        else:
            logging.warning(f"log_file: Valid options are: DEBUG, INFO, WARNING, ERROR and OFF")

    logging.info(f"Logging to console set to: {logging.getLevelName(logger.handlers[0].level)}")
    if logger.handlers.__len__() == 3:
        logging.info(f"Logging to file set to: {logging.getLevelName(logger.handlers[2].level)}")
    
    logging.debug(f'Inverter Config Loaded: {config_inverter}')    

    if config_inverter.get('host'):
        inverter = SungrowClient.SungrowClient(config_inverter)
    else:
        logging.error(f"Error: host option in config is required")
        sys.exit("Error: host option in config is required")

    if not inverter.checkConnection():
        logging.error(f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}")
        sys.exit(f"Error: Connection to inverter failed: {config_inverter.get('host')}:{config_inverter.get('port')}")       

    inverter.configure_registers(registersfile)
    if not inverter.inverter_config['connection'] == "http": inverter.close()
    
    # Now we know the inverter is working, lets load the exports
    exports = []
    if configfile.get('exports'):
        for export in configfile.get('exports'):
            try:
                if export.get('enabled', False):
                    export_load = importlib.import_module("exports." + export.get('name'))
                    logging.info(f"Loading Export: {export.get('name')}")
                    export_instance = getattr(export_load, "export_" + export.get('name'))()

                    if export_instance.configure(export, inverter):
                        exports.append(export_instance)
                        logging.info(f"Successfully configured export: {export.get('name')}")
                    else:
                        logging.error(f"Export {export.get('name')} configuration failed - skipping")
            except ModuleNotFoundError as err:
                logging.error(f"Export module not found: {export.get('name')}.py - {err}")
            except Exception as err:
                logging.error(f"Failed loading export {export.get('name')}: {err}")
                logging.debug(traceback.format_exc())

    scan_interval = config_inverter.get('scan_interval')

    signal.signal(signal.SIGTERM, handle_sigterm)

    # Core polling loop
    while True:
        loop_start = time.perf_counter()

        inverter.checkConnection()

        # Scrape the inverter
        try:
            success = inverter.scrape()
        except Exception as e:
            logging.exception(f"Failed to scrape: {e}")
            success = False

        if(success):
            for export in exports:
                try:
                    export.publish(inverter)
                except Exception as e:
                    logging.error(f"Export {export.__class__.__name__} failed: {e}")
                    logging.debug(traceback.format_exc())
            if not inverter.inverter_config['connection'] == "http": inverter.close()
        else:
            inverter.disconnect()
            logging.warning(f"Data collection failed, skipped exporting data. Retrying in {scan_interval} secs")

        loop_end = time.perf_counter()
        process_time = round(loop_end - loop_start, 2)
        logging.debug(f'Processing Time: {process_time} secs')

        if runonce:
            sys.exit(0)
        
        # Sleep until the next scan
        if scan_interval - process_time <= 1:
            logging.warning(f"SunGather is taking {process_time} to process, which is longer than interval {scan_interval}, Please increase scan interval")
            time.sleep(process_time)
        else:
            logging.info(f'Next scrape in {int(scan_interval - process_time)} secs')
            time.sleep(scan_interval - process_time)    

def handle_sigterm(signum, frame):
    print("Received SIGTERM, shutting down gracefully...")
    # Perform any cleanup here
    exit(0)

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger('')
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)
logger.addHandler(ch)

if __name__== "__main__":
    main()

sys.exit()
