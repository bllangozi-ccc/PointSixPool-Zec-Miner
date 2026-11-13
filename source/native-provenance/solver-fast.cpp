// Copyright (c) 2026 PointSixPool contributors. SPDX-License-Identifier: MIT
// Fresh exact-header Zcash Equihash200,9 solver using John Tromp's MIT algorithm.
#include "reviewed/equi_miner.h"
#include <array>
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <iostream>
#include <set>
#include <string>
#include <vector>

namespace {
volatile std::sig_atomic_t interrupted=0;
void stop(int signal){interrupted=signal;}
std::atomic<bool> cancelled{false};
std::chrono::steady_clock::time_point deadline;
int nibble(char c){if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;if(c>='A'&&c<='F')return c-'A'+10;return -1;}
bool readheader(std::array<char,140>& header){
 std::string line;line.reserve(282);char c;
 while(std::cin.get(c)){if(line.size()>=282)return false;line+=c;}
 if(std::cin.bad())return false;
 if(!line.empty()&&line.back()=='\n'){line.pop_back();if(!line.empty()&&line.back()=='\r')line.pop_back();}
 if(line.size()!=280)return false;
 for(size_t i=0;i<140;++i){int a=nibble(line[2*i]),b=nibble(line[2*i+1]);if(a<0||b<0)return false;header[i]=static_cast<char>((a<<4)|b);}
 return true;
}
int number(const std::string& s,int maximum){if(s.empty()||s.size()>3)return -1;int n=0;for(char c:s){if(c<'0'||c>'9')return -1;n=n*10+c-'0';}return n>=1&&n<=maximum?n:-1;}
// All workers reach both barriers before observing the shared stop decision.
// No thread can exit while another still waits for a participant in that round.
bool checkpoint(equi& eq,u32 id){
 int rc=pthread_barrier_wait(&eq.barry);if(rc&&rc!=PTHREAD_BARRIER_SERIAL_THREAD)std::_Exit(1);
 if(id==0 && (interrupted||std::chrono::steady_clock::now()>=deadline))cancelled.store(true,std::memory_order_relaxed);
 rc=pthread_barrier_wait(&eq.barry);if(rc&&rc!=PTHREAD_BARRIER_SERIAL_THREAD)std::_Exit(1);
 return cancelled.load(std::memory_order_relaxed);
}
void* solve(void* ptr){
 thread_ctx& ctx=*static_cast<thread_ctx*>(ptr);equi& eq=*ctx.eq;const u32 id=ctx.id;
 eq.digit0(id);if(checkpoint(eq,id))return nullptr;
 eq.digit1(id);if(checkpoint(eq,id))return nullptr;
 eq.digit2(id);if(checkpoint(eq,id))return nullptr;
 eq.digit3(id);if(checkpoint(eq,id))return nullptr;
 eq.digit4(id);if(checkpoint(eq,id))return nullptr;
 eq.digit5(id);if(checkpoint(eq,id))return nullptr;
 eq.digit6(id);if(checkpoint(eq,id))return nullptr;
 eq.digit7(id);if(checkpoint(eq,id))return nullptr;
 eq.digit8(id);if(checkpoint(eq,id))return nullptr;
 eq.digitK(id);checkpoint(eq,id);return nullptr;
}
// Original Tromp index packing: concatenate512 canonical21-bit indices, MSB first.
std::array<unsigned char,1344> compress(const proof sol){
 std::array<unsigned char,1344> out{};unsigned bits=0;uint64_t acc=0;size_t next=0;
 for(size_t i=0;i<PROOFSIZE;++i){if(sol[i]>=(1u<<21))throw std::runtime_error("index range");acc=(acc<<21)|sol[i];bits+=21;while(bits>=8){bits-=8;out[next++]=static_cast<unsigned char>(acc>>bits);}}
 if(next!=out.size()||bits)throw std::runtime_error("packing size");
 return out;
}
}
int main(int argc,char** argv){
 if(argc==2&&std::string(argv[1])=="--version"){std::cout<<"point6miner-equihash-fast 0.1.0 tromp-cpu zcash-200-9 header140 solution1344 threads1..16\n";return 0;}
 int threads=1,seconds=120;bool gotthreads=false,gottime=false;
 for(int i=1;i<argc;i+=2){
  if(i+1>=argc){std::cerr<<"incomplete option\n";return 2;}
  std::string option(argv[i]);int value;
  if(option=="--threads"&&!gotthreads&&(value=number(argv[i+1],16))>0){threads=value;gotthreads=true;}
  else if(option=="--max-seconds"&&!gottime&&(value=number(argv[i+1],300))>0){seconds=value;gottime=true;}
  else{std::cerr<<"invalid option or range\n";return 2;}
 }
 std::signal(SIGINT,stop);std::signal(SIGTERM,stop);std::signal(SIGPIPE,SIG_IGN);
 try{
  std::array<char,140> header{};if(!readheader(header)){std::cerr<<"expected one140-byte header as280hex characters\n";return 2;}
  if(interrupted)return 130;
  deadline=std::chrono::steady_clock::now()+std::chrono::seconds(seconds);
  equi eq(threads);
  eq.setheadernonce(header.data(),header.size(),"ZcashPoW");
  std::vector<thread_ctx> contexts(threads);
  for(int i=0;i<threads;++i){contexts[i].id=i;contexts[i].eq=&eq;if(pthread_create(&contexts[i].thread,nullptr,solve,&contexts[i])){std::cerr<<"worker creation failed\n";std::_Exit(1);}}
  for(auto& ctx:contexts)if(pthread_join(ctx.thread,nullptr)){std::cerr<<"worker join failed\n";std::_Exit(1);}
  if(interrupted)return 130;
  if(cancelled.load()) {std::cerr<<"solver time budget reached\n";return 124;}
  std::set<std::array<unsigned char,1344>> emitted;
  const u32 count=min(MAXSOLS,eq.nsols.load());
  for(u32 i=0;i<count;++i){
   if(interrupted)return 130;
   if(verify(eq.sols[i],header.data(),header.size(),"ZcashPoW")!=POW_OK)throw std::runtime_error("invalid native proof");
   auto bytes=compress(eq.sols[i]);if(!emitted.insert(bytes).second)continue;
   std::string hex;hex.resize(2688);const char* digits="0123456789abcdef";
   for(size_t j=0;j<bytes.size();++j){hex[2*j]=digits[bytes[j]>>4];hex[2*j+1]=digits[bytes[j]&15];}
   std::cout<<hex<<'\n'<<std::flush;if(!std::cout.good()){std::cerr<<"solution output failed\n";return 1;}
  }
  pthread_barrier_destroy(&eq.barry);return 0;
 }catch(const std::exception&){std::cerr<<"solver computation failed\n";return 1;}
}
