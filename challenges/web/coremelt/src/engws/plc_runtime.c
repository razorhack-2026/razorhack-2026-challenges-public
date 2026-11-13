/* Coremelt eng-ws soft-PLC: runs the matiec-compiled IEC program and serves it *)
   over Modbus/TCP :502 via libmodbus. Same control code OpenPLC runs; lighter runtime.
   %QW0-3 = trigger (holding, master-writable), %QW10..= flag out (holding, readable),
   %QX0.0 = GATE_OPEN (coil). */
#include "iec_std_lib.h"
#include <modbus/modbus.h>
#include <stdio.h>
#include <unistd.h>
IEC_BOOL __DEBUG;
TIME __CURRENT_TIME;
#define __LOCATED_VAR(TYPE, NAME, ...) TYPE NAME##_str; TYPE *NAME = &NAME##_str;
#include "LOCATED_VARIABLES.h"
#undef __LOCATED_VAR
extern void config_init__(void);
extern void config_run__(unsigned long tick);
#define NW 12
int main(void){
  WORD *ins[4]  = {__QW0, __QW1, __QW2, __QW3};
  WORD *outs[NW] = {__QW10, __QW11, __QW12, __QW13, __QW14, __QW15, __QW16, __QW17, __QW18, __QW19, __QW20, __QW21};
  int i, k;
  config_init__();
  modbus_t *ctx = modbus_new_tcp("127.0.0.1", 502); /* loopback only: shared task namespace */
  modbus_mapping_t *mb = modbus_mapping_new(16, 0, 32, 0);
  int s = modbus_tcp_listen(ctx, 4);
  fprintf(stderr, "coremelt PLC up: Modbus/TCP :502\n");
  for(;;){
    int fd = modbus_tcp_accept(ctx, &s);
    if(fd < 0) continue;
    for(;;){
      uint8_t q[MODBUS_TCP_MAX_ADU_LENGTH];
      int rc = modbus_receive(ctx, q);
      if(rc <= 0) break;
      modbus_reply(ctx, q, rc, mb);
      for(i=0;i<4;i++) *ins[i] = mb->tab_registers[i];
      config_run__(0);
      for(k=0;k<NW;k++) mb->tab_registers[10+k] = *outs[k];
      mb->tab_bits[0] = (*__QX0_0) ? 1 : 0;
    }
    close(fd);
  }
  return 0;
}
