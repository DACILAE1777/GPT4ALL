#include <napi.h>
#include "llmodel.h"
#include <iostream>
#include "llmodel_c.h" 
#include "prompt.h"
#include <atomic>
#include <memory>
#include <filesystem>
#include <set>
namespace fs = std::filesystem;

struct ModelDeleter
{
    void operator()(llmodel_model p) const
    {
        std::cout << "Debug: deleting model\n";
        llmodel_model_destroy(p);
    }
};

std::shared_ptr<llmodel_model> 
make_shared_model(llmodel_model* surface,
        const char *model_path,
        const char *build_variant,
        llmodel_error *error)
{
    return std::shared_ptr<llmodel_model>(surface, model_path, build_variant, error, ModelDeleter);
};

class NodeModelWrapper: public Napi::ObjectWrap<NodeModelWrapper> {
public:
  NodeModelWrapper(const Napi::CallbackInfo &);
  ~NodeModelWrapper();
  Napi::Value getType(const Napi::CallbackInfo& info);
  Napi::Value IsModelLoaded(const Napi::CallbackInfo& info);
  Napi::Value StateSize(const Napi::CallbackInfo& info);
  /**
   * Prompting the model. This entails spawning a new thread and adding the response tokens
   * into a thread local string variable.
   */
  Napi::Value Prompt(const Napi::CallbackInfo& info);
  void SetThreadCount(const Napi::CallbackInfo& info);
  Napi::Value getName(const Napi::CallbackInfo& info);
  Napi::Value ThreadCount(const Napi::CallbackInfo& info);
  Napi::Value GenerateEmbedding(const Napi::CallbackInfo& info);
  Napi::Value HasGpuDevice(const Napi::CallbackInfo& info);
  Napi::Value ListGpus(const Napi::CallbackInfo& info);
  Napi::Value InitGpuByString(const Napi::CallbackInfo& info);
  Napi::Value GetRequiredMemory(const Napi::CallbackInfo& info);
  Napi::Value GetGpuDevices(const Napi::CallbackInfo& info);
  /*
   * The path that is used to search for the dynamic libraries
   */
  Napi::Value GetLibraryPath(const Napi::CallbackInfo& info);
  /**
   * Creates the LLModel class
   */
  static Napi::Function GetClass(Napi::Env);
  llmodel_model GetInference();
private:
  /**
   * The underlying inference that interfaces with the C interface
   */
  std::shared_ptr<llmodel_model> inference_;

  std::string type;
  // corresponds to LLModel::name() in typescript
  std::string name;
  std::string full_model_path;
  static Napi::FunctionReference constructor;
};
