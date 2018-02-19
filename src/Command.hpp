#ifndef _MULTIRAXML_COMMAND_HPP_
#define _MULTIRAXML_COMMAND_HPP_

#include <string>
#include <memory>
#include <vector>
#include <map>
#include <stack>
#include "Common.hpp"

using namespace std;

class Command {
public:
  Command(const string &id, 
      bool isMpiCommand,
      unsigned int ranks,
      unsigned int estimatedCost,
      const vector<string> &arguments);
  virtual ~Command() {}
 
  const string &getId() const {return _id;}
  int getEstimatedCost() const {return _estimatedCost;}
  int getRanksNumber() const {return _ranksNumber;}
  bool isMpiCommand() const {return _isMpiCommand;}
  string toString() const;
  const vector<string> &getArgs() const {return _args;}
public:
  // initial information
  const string _id;
  const vector<string> _args;
  bool _isMpiCommand;
  int _ranksNumber;
  int _estimatedCost;
};
using CommandPtr = shared_ptr<Command>;

class CommandsContainer {
public:
  CommandsContainer(const string &commandsFilename);

  CommandPtr getCommand(string id) const;
  vector<CommandPtr> &getCommands() {return _commands;}
  const vector<CommandPtr> &getCommands() const {return _commands;}
private:
  void addCommand(CommandPtr command);

  vector<CommandPtr> _commands;
  map<string, CommandPtr> _dicoCommands;
};

class Instance {
public:
  Instance(CommandPtr command, int startingRank, int ranksNumber); 
  virtual void execute() = 0;
  
  const string &getId() const {return _command->getId();}
  bool didFinish() const {return _finished;}
  void onFinished();
  Time getStartTime() const {return _beginTime;} 
  int getElapsedMs() const {return Common::getElapsedMs(_beginTime, _endTime);}
  int getStartingRank() const {return _startingRank;} 
  int getRanksNumber() const {return _ranksNumber;}
protected:
  CommandPtr _command;
  int _startingRank;
  int _ranksNumber;
  Time _beginTime;
  Time _endTime;
  bool _finished;
};
using InstancePtr = shared_ptr<Instance>;
using InstancesHistoric = vector<InstancePtr>;

class RanksAllocator {
public:
  virtual ~RanksAllocator() {};
  virtual bool ranksAvailable() = 0;
  virtual bool allRanksAvailable() = 0;
  virtual InstancePtr allocateRanks(int requestedRanks, 
      CommandPtr command) = 0;
  virtual void freeRanks(InstancePtr instance) = 0;
};

class CommandsRunner {
public:
  CommandsRunner(const CommandsContainer &commandsContainer,
      unsigned int availableRanks,
      const string &outputDir);
  void run();
  const InstancesHistoric &getHistoric() const {return _historic;} 
private:
  
  static bool compareCommands(CommandPtr c1, CommandPtr c2);
  CommandPtr getPendingCommand() {return *_commandIterator;}
  bool isCommandsEmpty() {return _commandIterator == _commandsVector.end();}
  const string &getOutputDir() const {return _outputDir;}

  void executePendingCommand();
  void checkCommandsFinished();
  void onInstanceFinished(InstancePtr instance);
  
  const CommandsContainer &_commandsContainer;
  
  const unsigned int _availableRanks;
  const string _outputDir;

  shared_ptr<RanksAllocator> _allocator;
  vector<CommandPtr> _commandsVector;
  vector<CommandPtr>::iterator _commandIterator;
  map<string, InstancePtr> _startedInstances;
  InstancesHistoric _historic;
};

class RunStatistics {
public:
  RunStatistics(const InstancesHistoric &historic, 
      Time begin, 
      Time end,
      int availableRanks);
  void printGeneralStatistics();
  void exportSVG(const string &svgfile);
private:
  const InstancesHistoric &_historic;
  Time _begin;
  Time _end;
  int _availableRanks;
};

#endif
