using Point6Miner.Core;
using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using System.Runtime.CompilerServices;
using System.Diagnostics;
int seconds = args.Length == 0 ? 30 : int.Parse(args[0]);
if (seconds < 1 || seconds > 600) throw new ArgumentException("Bounded 1–600 second fixture only.");
string solverFixture=Path.Combine(Path.GetTempPath(),"pointsix-resource-fixture-"+Guid.NewGuid().ToString("N"));File.WriteAllText(solverFixture,"non-executed fixture");
try{string pin=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(solverFixture)));_ = new PinnedProcessSolver(solverFixture,pin,new SolverProcessLimits(MemoryMiB:6144,Threads:12));bool excessiveMemoryDenied=false;try{_ = new PinnedProcessSolver(solverFixture,pin,new SolverProcessLimits(MemoryMiB:8193,Threads:12));}catch(ArgumentException){excessiveMemoryDenied=true;}if(!excessiveMemoryDenied)throw new Exception("Solver memory ceiling was not enforced");}finally{File.Delete(solverFixture);}
var watch=Stopwatch.StartNew();int sessions=0,jobs=0;
while(watch.Elapsed.TotalSeconds<seconds){var result=await Exercise(false);if(result!.StopReason!="connection-ended"||result.Submitted!=0||result.Uncertain!=0||result.Jobs<2)throw new Exception("Clean disconnect did not preserve exact result");sessions++;jobs+=result.Jobs;}
bool denied=false;try{await Exercise(true);}catch(InvalidDataException){denied=true;}if(!denied)throw new Exception("Authorization refusal must not become a retryable transport result");
Console.WriteLine(JsonSerializer.Serialize(new{passed=true,seconds=watch.Elapsed.TotalSeconds,sessions,jobs,authorizationRefusalHeld=denied,publicPoolContact=false,proofsSubmitted=0}));
static async Task<StratumRunResult?> Exercise(bool deny){
 using var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();int port=((IPEndPoint)listener.LocalEndpoint).Port;
 Task serve=Task.Run(async()=>{using var client=await listener.AcceptTcpClientAsync();using var stream=client.GetStream();using var input=new StreamReader(stream);using var output=new StreamWriter(stream){AutoFlush=true};
 for(int i=0;i<2;i++){using var req=JsonDocument.Parse((await input.ReadLineAsync())!);var id=req.RootElement.GetProperty("id").GetInt32();object result=i==0?new object[]{Array.Empty<object>(),"abcdef"}:!deny;await output.WriteLineAsync(JsonSerializer.Serialize(new{id,result,error=(object?)null}));}
 if(deny)return;
 await output.WriteLineAsync(JsonSerializer.Serialize(new{method="mining.set_target",@params=new[]{new string('f',64)}}));
 for(int i=0;i<10;i++){await output.WriteLineAsync(JsonSerializer.Serialize(new{method="mining.notify",@params=new object[]{"fixture"+i,"04000000",new string('0',64),new string('0',64),new string('0',64),"00000000","ffff001d",true}}));await Task.Delay(50);}
 });
 try{return await new ZecStratumMiner().RunAsync(new(new Uri($"stratum+tcp://127.0.0.1:{port}"),"fixtureID","Lifecycle",Mine:true,MaxSeconds:5,RegisteredIdentity:true),new WaitingSolver());}finally{await serve;}
}
sealed class WaitingSolver:IMiningWorkSolver{
 public MiningAlgorithm Algorithm=>MiningAlgorithm.ZcashEquihash2009;
 public async IAsyncEnumerable<byte[]> SolveAsync(ReadOnlyMemory<byte> header,[EnumeratorCancellation]CancellationToken token){await Task.Delay(10000,token);yield break;}
}
