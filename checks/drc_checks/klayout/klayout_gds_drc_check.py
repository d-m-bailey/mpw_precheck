import argparse
import logging
import subprocess
import os
from pathlib import Path

def klayout_gds_drc_check(check_name, drc_script_path, gds_input_file_path, output_directory, klayout_cmd_extra_args=[]):
    logging.info("in CUSTOM klayout_gds_drc_check")
    report_file_path = output_directory / 'outputs/reports' / f'{check_name}_check.xml'
    logs_directory = output_directory / 'logs'
    total_file_path = logs_directory / f'{check_name}_check.total'
    run_drc_check_cmd = ['klayout', '-b', '-r', drc_script_path,
                         '-rd', f"input={gds_input_file_path}",
                         '-rd', f"topcell={gds_input_file_path.stem}",
                         '-rd', f"report={report_file_path}"]
    run_drc_check_cmd.extend(klayout_cmd_extra_args)

    log_file_path = logs_directory / f'{check_name}_check.log'
    cmd = ' '.join(str(x) for x in run_drc_check_cmd) + ' >& ' + str(log_file_path)
    with open(log_file_path, 'w') as klayout_drc_log:
        logging.info(f"run: {cmd}") # helpful reference, print long-cmd once & messages below remain concise
        p = subprocess.run(run_drc_check_cmd, stderr=klayout_drc_log, stdout=klayout_drc_log)
        # Check exit-status of all subprocesses
        stat = p.returncode
        if stat != 0:
            logging.error(f"ERROR {check_name} FAILED, stat={stat}, see {log_file_path}")
            return False

    try:
        with open(report_file_path) as klayout_xml_report:
            size = os.fstat(klayout_xml_report.fileno()).st_size
            if size == 0:
                logging.error(f"ERROR {check_name} WROTE DEGENERATE {report_file_path.name}: empty")
                return False
            drc_content = klayout_xml_report.read()
            drc_count = drc_content.count('<item>')
            with open(total_file_path, 'w') as drc_total:
                drc_total.write(f"{drc_count}")
            if drc_count == 0:
                logging.info("No DRC Violations found")
                return True
            else:
                logging.error(f"Total # of DRC violations is {drc_count} Please check {report_file_path} For more details")
                return False
    # Catch reports not found (vs crude abort with exception).
    except FileNotFoundError as e:
        logging.error(f"ERROR {check_name} FAILED TO GENERATE {report_file_path.name}: {e}")
    except (IOError, OSError) as e:
        logging.error(f"ERROR {check_name} FAILED TO GENERATE {total_file_path.name}: {e}")

    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format=f"%(asctime)s | %(levelname)-7s | %(message)s", datefmt='%d-%b-%Y %H:%M:%S')
    parser = argparse.ArgumentParser(description='Runs magic and klayout drc checks on a given GDS.')
    parser.add_argument('--gds_input_file_path', '-g', required=True, help='GDS File to apply DRC checks on')
    parser.add_argument('--output_directory', '-o', required=True, help='Output Directory')
    parser.add_argument('--feol', '-f', action='store_true', required=False, default=False, help='run FEOL rules')
    parser.add_argument('--beol', '-b', action='store_true', required=False, default=False, help='run BEOL rules')
    parser.add_argument('--off_grid', '-og', action='store_true', required=False, default=False, help='run OFFGRID rules')
    args = parser.parse_args()

    gds_input_file_path = Path(args.gds_input_file_path)
    output_directory = Path(args.output_directory)

    klayout_sky130A_mr_drc_script_path = Path(__file__).parent.parent.parent / "tech-files/sky130A_mr.drc"

    extra_args = []
    if args.feol:
        extra_args.append("-rd")
        extra_args.append("feol=true")
    if args.beol:
        extra_args.append("-rd")
        extra_args.append("beol=true")
    if args.off_grid:
        extra_args.append("-rd")
        extra_args.append("offgrid=true")

    if gds_input_file_path.exists() and gds_input_file_path.suffix == ".gds":
        if output_directory.exists() and output_directory.is_dir():
            if klayout_gds_drc_check("klayout_drc", klayout_sky130A_mr_drc_script_path, gds_input_file_path, output_directory, extra_args):
                logging.info("Klayout GDS DRC Clean")
            else:
                logging.info("Klayout GDS DRC Dirty")
        else:
            logging.error(f"{output_directory} is not valid")
    else:
        logging.error(f"{gds_input_file_path} is not valid")
