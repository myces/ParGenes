import os
import sys
import shutil



logsFile = "/home/morelbt/github/phd_experiments/results/multi-raxml/fromfastadir/haswell_256/ensembl_2/submit.sh.out"
commandFile = "/home/morelbt/github/phd_experiments/results/multi-raxml/fromfastadir/haswell_256/ensembl_2/second_command.txt"
ranks = 16

debugPath = "/home/morelbt/github/phd_experiments/debug/"
replayCommand = os.path.join(debugPath, "command.txt")
replayOutput = os.path.join(debugPath, "replay_output")

try:
  shutil.rmtree(replayOutput) 
except:
  pass

os.makedirs(replayOutput)


startPrefix = "## Started"
endPrefix = "End of"

dicoFinished = {}
dicoCommands = {}

lines = open(logsFile).readlines()
for line in lines:
  if (line.startswith(startPrefix)):
    dicoFinished[line.split(" ")[2]] = 1
  elif (line.startswith(endPrefix)):
    dicoFinished[line.split(" ")[2]] = 0

lines = open(commandFile).readlines()
for line in lines:
  dicoCommands[line.split(" ")[0]] = line[:-1] + " --redo \n"

with open(replayCommand, "w") as writer:
  for command, value in dicoFinished.items():
    if (value == 1):
      writer.write(dicoCommands[command])

print("mpirun -np 1 /home/morelbt/github/multi-raxml/build/multi-raxml --spawn-scheduler " + replayCommand + " " + replayOutput + " 16 ") 


