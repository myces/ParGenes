

#include "Command.hpp"
#include "Common.hpp"
#include <iostream>
#include <fstream>
#include <sstream>
#include <iterator>
#include <algorithm>
#include "spawn_implem/SpawnImplem.h"


Command::Command(const string &id, 
    bool isMpiCommand,
    unsigned int ranks,
    unsigned int estimatedCost,
    const vector<string> &arguments):
  _id(id),
  _args(arguments),
  _isMpiCommand(isMpiCommand),
  _ranksNumber(ranks),
  _estimatedCost(estimatedCost)
{
}

string Command::toString() const 
{
  string res;
  res = getId() + " ";
  res += string(_isMpiCommand ? "mpi" : "seq") + " ";
  for (auto str: _args) {
    res += str + " ";
  }
  res += "{ranks: " + to_string(getRanksNumber()) + ", estimated cost: "; 
  res += to_string(getEstimatedCost()) + "}";
  return res;
}
  
  
Instance::Instance(CommandPtr command,
    int startingRank,
    int ranksNumber):
  _command(command),
  _startingRank(startingRank),
  _ranksNumber(ranksNumber),
  _finished(false)
{
  
}

void Instance::onFinished()
{
  _finished = true;
  _endTime = Common::getTime();
}

static inline void rtrim(std::string &s) {
  s.erase(std::find_if(s.rbegin(), s.rend(), [](int ch) {
        return !std::isspace(ch);
        }).base(), s.end());
}

// Read a line in a commands file and skip comments
// discards empty lines
bool readNextLine(ifstream &is, string &os)
{
  while (getline(is, os)) {
    auto end = os.find("#");
    if (string::npos != end)
      os = os.substr(0, end);
    rtrim(os);
    if (os.size()) 
      return true;
  }
  return false;
}



CommandsContainer::CommandsContainer(const string &commandsFilename)
{
  ifstream reader(commandsFilename);
  if (!reader)
    throw MultiRaxmlException("Cannot open commands file ", commandsFilename);
  
  string line;
  while (readNextLine(reader, line)) {
    
    string id;
    string isMPIStr;
    int ranks;
    int estimatedCost;
    
    istringstream iss(line);
    iss >> id;
    iss >> isMPIStr;
    iss >> ranks;
    iss >> estimatedCost;
    
    bool isMPI = (isMPIStr == string("mpi"));
    vector<string> commandVector;
    while (!iss.eof()) {
      string plop;
      iss >> plop;
      commandVector.push_back(plop);
    }
    CommandPtr command(new Command(id, isMPI, ranks, estimatedCost, commandVector));
    addCommand(command);
  }
}

void CommandsContainer::addCommand(CommandPtr command)
{
  _commands.push_back(command); 
  _dicoCommands[command->getId()] = command;
}

CommandPtr CommandsContainer::getCommand(string id) const
{
  auto res =  _dicoCommands.find(id);
  if (res == _dicoCommands.end())
    return CommandPtr(0);
  else 
    return res->second;
}

CommandsRunner::CommandsRunner(const CommandsContainer &commandsContainer,
      unsigned int availableRanks,
      const string &outputDir):
  _commandsContainer(commandsContainer),
  _availableRanks(availableRanks),
  _outputDir(outputDir),
  _allocator(new SpawnedRanksAllocator(availableRanks, outputDir)),
  _commandsVector(commandsContainer.getCommands())
{
  sort(_commandsVector.begin(), _commandsVector.end(), compareCommands);
  _commandIterator = _commandsVector.begin();

}

void CommandsRunner::run() 
{
  Timer timer;
  while (!_allocator->allRanksAvailable() || !isCommandsEmpty()) {
    if (!isCommandsEmpty()) {
      auto  nextCommand = getPendingCommand();
      if (_allocator->ranksAvailable()) {
        executePendingCommand();
        continue;
      }
    }
    checkCommandsFinished();
  }
}

bool CommandsRunner::compareCommands(CommandPtr c1, CommandPtr c2)
{
  if (c2->getRanksNumber() == c1->getRanksNumber()) {
    return c2->getEstimatedCost() < c1->getEstimatedCost();
  }
  return c2->getRanksNumber() < c1->getRanksNumber();
}

  
void CommandsRunner::executePendingCommand()
{
  auto command = getPendingCommand();
  InstancePtr instance = _allocator->allocateRanks(command->getRanksNumber(), command);
  cout << "Executing command " << command->toString() << " on ranks [" 
    << instance->getStartingRank() + instance->getRanksNumber() - 1 
    << "]"  << endl;
  instance->execute();
  _startedInstances[instance->getId()] = instance;
  _historic.push_back(instance);
  _commandIterator++;
}

void CommandsRunner::checkCommandsFinished()
{
  vector<string> files;
  Common::readDirectory(_outputDir, files);
  for (auto file: files) {
    auto instance = _startedInstances.find(file);
    if (instance != _startedInstances.end()) {
      onInstanceFinished(instance->second);
    }
  }
}

void CommandsRunner::onInstanceFinished(InstancePtr instance)
{
  string fullpath = _outputDir + "/" + instance->getId(); // todobenoit not portable
  Common::removefile(fullpath);
  if (instance->didFinish()) {
    return; // sometime the file is written several times :(
  }
  _allocator->freeRanks(instance);
  cout << "Command " << instance->getId() << " finished after ";
  instance->onFinished();
  cout << instance->getElapsedMs() << "ms" << endl;
}

RunStatistics::RunStatistics(const InstancesHistoric &historic,
    Time begin,
    Time end,
    int availableRanks):
  _historic(historic),
  _begin(begin),
  _end(end),
  _availableRanks(availableRanks)
{

}

void RunStatistics::printGeneralStatistics()
{
  int totalElapsedTime = Common::getElapsedMs(_begin, _end);
  int cumulatedTime = 0;
  int longestTime = 0;
  for (auto instance: _historic) {
    cumulatedTime += instance->getElapsedMs() * instance->getRanksNumber();
    longestTime = max(longestTime, instance->getElapsedMs());
  }
  double ratio = double(cumulatedTime) / double(_availableRanks * totalElapsedTime);
  
  cout << "Finished running commands. Total elasped time: ";
  cout << totalElapsedTime << "ms" << endl;
  cout << "The longest command took " << longestTime << "ms" << endl;
  cout << "Load balance ratio: " << ratio << endl;
}

string get_random_hex()
{
  static const char *buff = "0123456789abcdef";
  char res[8];
  res[0] = '#';
  res[7] = 0;
  for (int i = 0; i < 6; ++i) {
    res[i+1] = buff[rand() % 16];
  }
  return string(res);
}

void RunStatistics::exportSVG(const string &svgfile) 
{
  cout << "Saving svg output in " << svgfile << endl;
  ofstream os(svgfile, std::ofstream::out);
  if (!os) {
    cerr << "Warning: cannot open  " << svgfile << ". Skipping svg export." << endl;
    return; 
  }
  int totalWidth = _availableRanks + 1;
  int totalHeight = Common::getElapsedMs(_begin, _end);
  double ratioWidth = 500.0 / double(totalWidth);
  double ratioHeight = 500.0 / double(totalHeight);
   
  os << "<svg  xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\">" << endl;
  os << "  <svg x=\"0\" y=\"0.0\" width=\"" << ratioWidth << "\" height=\"500.0\" >" << endl;
  os << "    <rect x=\"0%\" y=\"0%\" height=\"100%\" width=\"100%\" style=\"fill: #ffffff\"/>" << endl;
  os << "  </svg>" << endl;

  for (auto instance: _historic) {
    os << "  <svg x=\"" << ratioWidth * instance->getStartingRank()
       << "\" y=\"" << ratioHeight * Common::getElapsedMs(_begin, instance->getStartTime()) << "\" "
       << "width=\"" << ratioWidth * instance->getRanksNumber() << "\" " 
       << "height=\""  << ratioHeight * instance->getElapsedMs() << "\" >" << endl;
    string color = get_random_hex(); 
    os << "    <rect x=\"0%\" y=\"0%\" height=\"100%\" width=\"100%\" style=\"fill: "
       << color  <<  "\"/>" << endl;
    os << "  </svg>" << endl;
  }
  os << "</svg>" << endl;
}

