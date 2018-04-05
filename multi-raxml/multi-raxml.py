import sys
import os
import subprocess
import time
import shutil

def get_mpi_scheduler_exec():
  repo_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
  return os.path.join(repo_root, "mpi-scheduler", "build", "mpi-scheduler")

def sites_to_maxcores(sites):
  if sites == 0:
    return 0
  return 1 << ((sites // 1000)).bit_length()

def parse_msa_info(log_file):
  result = [0, 0]
  unique_sites = 0
  try:
    lines = open(log_file).readlines()
  except:
    print("Cannot find file " + log_file)
    return result
  for line in lines:
    if "Alignment comprises" in line:
      unique_sites = int(line.split(" ")[5])
    if "taxa" in line:
      result[1] = int(line.split(" ")[4])
  result[0] = sites_to_maxcores(unique_sites)
  return result

def run_mpi_scheduler(raxml_library, commands_filename, output_dir, ranks):
  sys.stdout.flush()
  command = []
  command.append("mpirun")
  command.append("-np")
  command.append(str(ranks))
  command.append(get_mpi_scheduler_exec())
  command.append(implementation)
  command.append(raxml_library)
  command.append(commands_filename)
  command.append(output_dir)
  print ("Calling mpi-scheduler: " + " ".join(command))
  subprocess.check_call(command)

def build_first_command(fasta_files, output_dir, options, ranks):
  first_commands_file = os.path.join(output_dir, "first_command.txt")
  first_run_output_dir = os.path.join(output_dir, "first_run")
  first_run_results = os.path.join(first_run_output_dir, "results")
  os.makedirs(first_run_results)
  fasta_chuncks = []
  fasta_chuncks.append([])
  with open(first_commands_file, "w") as writer:
    for fasta in fasta_files:
      base = os.path.splitext(os.path.basename(fasta))[0]
      fasta_output_dir = os.path.join(first_run_results, base)
      os.makedirs(fasta_output_dir)
      writer.write("first_" + base + " 1 1 ")
      writer.write(" --parse ")
      writer.write( " --msa " + fasta + " " + options[:-1])
      writer.write(" --prefix " + os.path.join(fasta_output_dir, base))
      writer.write(" --threads 1 ")
      writer.write("\n")
  return first_commands_file

def build_second_command(fasta_files, output_dir, options, bootstraps, ranks):
  second_commands_file = os.path.join(output_dir, "second_command.txt")
  first_run_output_dir = os.path.join(output_dir, "first_run")
  first_run_results = os.path.join(first_run_output_dir, "results")
  second_run_output_dir = os.path.join(output_dir, "second_run")
  second_run_results = os.path.join(second_run_output_dir, "results")
  second_run_bootstraps = os.path.join(second_run_output_dir, "bootstraps")
  os.makedirs(second_run_results)
  if (bootstraps != 0):
    os.makedirs(second_run_bootstraps)
  with open(second_commands_file, "w") as writer:
    for fasta in fasta_files:
      base = os.path.splitext(os.path.basename(fasta))[0]
      first_fasta_output_dir = os.path.join(first_run_results, base)
      second_fasta_output_dir = os.path.join(second_run_results, base)
      os.makedirs(second_fasta_output_dir)
      first_run_log = os.path.join(os.path.join(first_fasta_output_dir, base + ".raxml.log"))
      uncompressed_fasta = fasta
      compressed_fasta = os.path.join(os.path.join(first_fasta_output_dir, base + ".raxml.rba"))
      parse_result = parse_msa_info(first_run_log)
      cores = str(parse_result[0])
      taxa = str(parse_result[1])
      if (cores == "0" or taxa == "0"):
        print("warning with fasta " + fasta + ", skipping")
        continue
      writer.write("second_" + base + " ")
      writer.write(cores + " " + taxa )
      writer.write(" --msa " + compressed_fasta + " " + options[:-1])
      writer.write(" --prefix " + os.path.join(second_fasta_output_dir, base))
      writer.write(" --threads 1 ")
      writer.write("\n")
      bs_output_dir = os.path.join(second_run_bootstraps, base)
      os.makedirs(bs_output_dir)
      chunk_size = 1
      if (bootstraps > 30): # arbitrary threshold... todobenoit!
        chunk_size = 10
      for current_bs in range(0, (bootstraps - 1) // chunk_size + 1):
        bsbase = base + "_bs" + str(current_bs)
        bs_number = min(chunk_size, bootstraps - current_bs * chunk_size)
        writer.write(bsbase + " ")
        writer.write(cores + " " + taxa )
        writer.write(" --bootstrap")
        writer.write(" --msa " + uncompressed_fasta + " " + options[:-1])
        writer.write(" --prefix " + os.path.join(bs_output_dir, bsbase))
        writer.write(" --threads 1 ")
        writer.write(" --seed " + str(current_bs))
        writer.write(" --bs-trees " + str(bs_number))
        writer.write("\n")
         
  return second_commands_file

def concatenate_bootstraps(output_dir):
  start = time.time()
  print("concatenate_bootstraps")
  concatenated_dir = os.path.join(output_dir, "concatenated_bootstraps")
  try:
    print("todobenoit remove the try catch")
    os.makedirs(concatenated_dir)
  except:
    pass
  bootstraps_dir = os.path.join(output_dir, "second_run", "bootstraps")
  for fasta in os.listdir(bootstraps_dir):
    concatenated_file = os.path.join(concatenated_dir, fasta + ".bs")
    with open(concatenated_file,'wb') as writer:
      fasta_bs_dir = os.path.join(bootstraps_dir, fasta)
      for bs_file in os.listdir(fasta_bs_dir):
        if (bs_file.endswith("bootstraps")):
          with open(os.path.join(fasta_bs_dir, bs_file),'rb') as reader:
            try:
              shutil.copyfileobj(reader, writer)
            except OSError as e:
              print("ERROR!")
              print("OS error when copying " + os.path.join(fasta_bs_dir, bs_file) + " to " + concatenated_file)
              raise e
              
  end = time.time()
  print("concatenation time: " + str(end-start) + "s")

def build_supports_commands(output_dir):
  ml_trees_dir = os.path.join(output_dir, "second_run", "results")
  concatenated_dir = os.path.join(output_dir, "concatenated_bootstraps")
  supports_commands_file = os.path.join(output_dir, "supports_commands.txt")
  support_dir = os.path.join(output_dir, "supports_run")
  try:
    print("todobenoit remove try catch")
    os.makedirs(support_dir)
  except:
    pass
  print("Writing supports commands in " + supports_commands_file)
  with open(supports_commands_file, "w") as writer:
    for fasta in os.listdir(ml_trees_dir):
      ml_tree = os.path.join(ml_trees_dir, fasta, fasta + ".raxml.bestTree")
      bs_trees = os.path.join(concatenated_dir, fasta + ".bs")
      writer.write("support_" + fasta + " 1 1")
      writer.write(" --support")
      writer.write(" --tree " + ml_tree)
      writer.write(" --bs-trees " + bs_trees)
      writer.write(" --threads 1")
      writer.write(" --prefix " + os.path.join(support_dir, fasta + ".support"))
      writer.write("\n") 
  return supports_commands_file
    


def main_raxml_runner(implementation, fasta_dir, output_dir, options_file, bootstraps, ranks):
  try:
    os.makedirs(output_dir)
  except:
    pass
  scriptdir = os.path.dirname(os.path.realpath(__file__))
  raxml_library = os.path.join(scriptdir, "..", "raxml-ng", "bin", "raxml-ng-mpi.so")
  print("Results in " + output_dir)
  fasta_files = [os.path.join(fasta_dir, f) for f in os.listdir(fasta_dir)]
  options = open(options_file, "r").readlines()[0]
  first_commands_file = build_first_command(fasta_files, output_dir, options, ranks)
  run_mpi_scheduler(raxml_library, first_commands_file, os.path.join(output_dir, "first_run"), ranks)
  print("### end of first mpi-scheduler run")
  second_commands_file = build_second_command(fasta_files, output_dir, options, bootstraps, ranks)
  print("### end of build_second_command")
  run_mpi_scheduler(raxml_library, second_commands_file, os.path.join(output_dir, "second_run"), ranks)
  print("### end of second mpi-scheduler run")
  concatenate_bootstraps(output_dir)
  print("### end of bootstraps concatenation")
  supports_commands_file = build_supports_commands(output_dir)
  print("### end of build_supports_command")
  run_mpi_scheduler(raxml_library, supports_commands_file, os.path.join(output_dir, "supports_run"), ranks)
  print("### end of supports mpi-scheduler run")

def print_help():
  print("python raxml_runner.py --split-scheduler fasta_dir output_dir additionnal_options_file bootstraps_number cores_number")

if (len(sys.argv) != 7):
    print_help()
    sys.exit(0)


implementation = sys.argv[1]
fasta_dir = sys.argv[2] 
output_dir = sys.argv[3]
options_file = sys.argv[4]
bootstraps = int(sys.argv[5])
ranks = sys.argv[6]
start = time.time()
main_raxml_runner(implementation, fasta_dir, output_dir, options_file, bootstraps, ranks)
end = time.time()
print("TOTAL ELAPSED TIME SPENT IN " + os.path.basename(__file__) + " " + str(end-start) + "s")
