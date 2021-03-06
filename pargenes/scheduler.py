import sys
import subprocess
import os
import commons

def get_mpi_scheduler_exec():
  """ Get the path to the mpi scheduler executable """
  repo_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
  return os.path.join(repo_root, "mpi-scheduler", "build", "mpi-scheduler")

def run_mpi_scheduler(library, scheduler, commands_filename, output_dir, ranks, op):
  """ Run the mpi scheduler program """
  sys.stdout.flush()
  command = []
  command.append("mpiexec")
  command.append("-n")
  command.append(str(ranks))
  if (op.valgrind):
    command.append("--mca")
    command.append("btl")
    command.append("tcp,self")
    command.append("valgrind")
  command.append(get_mpi_scheduler_exec())
  if (scheduler == "onecore"):
    command.append("--onecore-scheduler")
  else:
    command.append("--split-scheduler")
  command.append(library)
  command.append(commands_filename)
  command.append(output_dir)
  
  logs_file = commons.get_log_file(output_dir, "logs")
  out = open(logs_file, "w")
  print("Calling mpi-scheduler: " + " ".join(command))
  print("Logs will be redirected to " + logs_file)
  p = subprocess.Popen(command, stdout=out, stderr=out)
  p.wait()
  errorcode = p.returncode
  if (errorcode != 0):
    print("mpi-scheduler execution failed with error code " + str(errorcode))
    print("Will now exit...")
    raise RuntimeError("mpi-scheduler  execution failed with error code " + str(errorcode))

