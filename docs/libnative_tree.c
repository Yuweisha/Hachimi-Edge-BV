/* ===== 0x03bd10  237 行 ===== */
// FUN_7ffa1b03bd10 @ 0x7ffa1b03bd10
// signature: undefined FUN_7ffa1b03bd10()
// ==================================================================

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int FUN_7ffa1b03bd10(longlong param_1,longlong param_2,longlong param_3,undefined8 *param_4)

{
  longlong *plVar1;
  undefined8 *puVar2;
  undefined8 *puVar3;
  code *pcVar4;
  int iVar5;
  int iVar6;
  ulonglong uVar7;
  longlong *plVar8;
  longlong lVar9;
  undefined8 local_res8;
  longlong local_res10;
  longlong local_res18;
  undefined8 *local_res20;
  undefined8 *local_58;
  undefined4 local_50;
  
  _DAT_7ffa1b3a18a8 = _DAT_7ffa1b3a18a8 + 1;
  plVar1 = param_4 + 2;
  local_res10 = param_2;
  local_res18 = param_3;
  local_res20 = param_4;
  if (*(longlong *)(param_1 + 0x18) == 0) {
    iVar5 = FUN_7ffa1b046d10(plVar1,param_3 + 0x20,param_3 + 0x20);
    if (iVar5 != 0) {
      return iVar5;
    }
    pcVar4 = *(code **)(param_1 + 0x90);
    if (pcVar4 == (code *)0x0) {
      iVar5 = FUN_7ffa1b048740(plVar1,plVar1,param_1 + 8);
    }
    else {
      if (*(short *)(param_4 + 3) < 0) {
        local_58 = &local_res8;
        local_res8 = 0;
        local_50 = 0x10001;
        iVar5 = FUN_7ffa1b046600(plVar1,&local_58);
        if (iVar5 != 0) {
          return -0x4f80;
        }
      }
      uVar7 = FUN_7ffa1b045fd0(plVar1);
      if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar7) {
        return -0x4f80;
      }
      iVar5 = (*pcVar4)(plVar1);
      if (iVar5 == 0) {
        if (*(short *)(param_4 + 3) < 0) {
          local_res8 = 0;
          do {
            local_58 = &local_res8;
            local_50 = 0x10001;
            iVar6 = FUN_7ffa1b046600(plVar1,&local_58);
            if (iVar6 == 0) break;
            iVar5 = FUN_7ffa1b0469c0(plVar1,plVar1,param_1 + 8,1);
            if (iVar5 != 0) goto LAB_7ffa1b03be65;
          } while (*(short *)(param_4 + 3) < 0);
        }
        iVar6 = FUN_7ffa1b046600(plVar1,param_1 + 8);
        while ((-1 < iVar6 && (iVar5 = FUN_7ffa1b046830(plVar1,plVar1,param_1 + 8), iVar5 == 0))) {
          iVar6 = FUN_7ffa1b046600(plVar1,param_1 + 8);
        }
      }
    }
LAB_7ffa1b03be65:
    if (iVar5 != 0) {
      return iVar5;
    }
    puVar2 = param_4 + 4;
    _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
    iVar5 = FUN_7ffa1b0469c0(puVar2,local_res18,plVar1,1);
    if (iVar5 == 0) {
      iVar6 = FUN_7ffa1b046600(puVar2,param_1 + 8);
      while ((-1 < iVar6 && (iVar5 = FUN_7ffa1b046830(puVar2,puVar2,param_1 + 8), iVar5 == 0))) {
        iVar6 = FUN_7ffa1b046600(puVar2,param_1 + 8);
      }
    }
    if (iVar5 != 0) {
      return iVar5;
    }
    puVar3 = param_4 + 6;
    iVar5 = FUN_7ffa1b0469c0(puVar3,local_res18,plVar1,0xffffffff);
    if ((iVar5 == 0) && (*(short *)(param_4 + 7) < 0)) {
      local_res8 = 0;
      do {
        local_58 = &local_res8;
        local_50 = 0x10001;
        iVar6 = FUN_7ffa1b046600(puVar3,&local_58);
        if (iVar6 == 0) break;
        iVar5 = FUN_7ffa1b0469c0(puVar3,puVar3,param_1 + 8,1);
        if (iVar5 != 0) {
          return iVar5;
        }
        iVar5 = 0;
      } while (*(short *)(param_4 + 7) < 0);
    }
    if (iVar5 != 0) {
      return iVar5;
    }
    iVar5 = FUN_7ffa1b0398e0(param_1,plVar1,puVar2,puVar3);
    param_4 = local_res20;
    if (iVar5 != 0) {
      return iVar5;
    }
    iVar5 = FUN_7ffa1b039ba0(param_1,local_res20,plVar1);
  }
  else {
    iVar5 = FUN_7ffa1b046d10(plVar1,param_3);
    if (iVar5 != 0) {
      return iVar5;
    }
    pcVar4 = *(code **)(param_1 + 0x90);
    if (pcVar4 == (code *)0x0) {
      iVar5 = FUN_7ffa1b048740(plVar1,plVar1,param_1 + 8);
    }
    else {
      if (*(short *)(param_4 + 3) < 0) {
        local_58 = &local_res8;
        local_res8 = 0;
        local_50 = 0x10001;
        iVar5 = FUN_7ffa1b046600(plVar1,&local_58);
        if (iVar5 != 0) {
          return -0x4f80;
        }
      }
      uVar7 = FUN_7ffa1b045fd0(plVar1);
      if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar7) {
        return -0x4f80;
      }
      iVar5 = (*pcVar4)(plVar1);
      if (iVar5 == 0) {
        if (*(short *)(param_4 + 3) < 0) {
          local_res8 = 0;
          do {
            local_58 = &local_res8;
            local_50 = 0x10001;
            iVar6 = FUN_7ffa1b046600(plVar1,&local_58);
            if (iVar6 == 0) break;
            iVar5 = FUN_7ffa1b0469c0(plVar1,plVar1,param_1 + 8,1);
            if (iVar5 != 0) goto LAB_7ffa1b03c0a5;
          } while (*(short *)(param_4 + 3) < 0);
        }
        iVar6 = FUN_7ffa1b046600(plVar1,param_1 + 8);
        while ((-1 < iVar6 && (iVar5 = FUN_7ffa1b046830(plVar1,plVar1,param_1 + 8), iVar5 == 0))) {
          iVar6 = FUN_7ffa1b046600(plVar1,param_1 + 8);
        }
      }
    }
LAB_7ffa1b03c0a5:
    if (iVar5 != 0) {
      return iVar5;
    }
    _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
    uVar7 = (ulonglong)*(ushort *)((longlong)param_4 + 0x1a);
    if (uVar7 != 0) {
      plVar8 = (longlong *)(*plVar1 + (uVar7 - 1) * 8);
      do {
        if (*plVar8 != 0) {
          iVar5 = FUN_7ffa1b045900(param_4,uVar7 + 1);
          if ((iVar5 == 0) && (iVar5 = FUN_7ffa1b045c10(param_4,plVar1), iVar5 == 0)) {
            FUN_7ffa1b074e60(*param_4,*(undefined2 *)((longlong)param_4 + 10),*plVar1,uVar7,2);
          }
          goto LAB_7ffa1b03c0ef;
        }
        plVar8 = plVar8 + -1;
        uVar7 = uVar7 - 1;
      } while (uVar7 != 0);
    }
    iVar5 = FUN_7ffa1b045d10(param_4,0);
LAB_7ffa1b03c0ef:
    if (iVar5 != 0) {
      return iVar5;
    }
    iVar6 = FUN_7ffa1b046600(param_4,param_1 + 8);
    iVar5 = 0;
    while ((-1 < iVar6 && (iVar5 = FUN_7ffa1b046830(param_4,param_4,param_1 + 8), iVar5 == 0))) {
      iVar6 = FUN_7ffa1b046600(param_4,param_1 + 8);
    }
    if (iVar5 != 0) {
      return iVar5;
    }
    local_58 = &local_res8;
    local_res8 = 0;
    local_50 = 0x10001;
    iVar5 = FUN_7ffa1b046600(param_1 + 0x18,&local_58);
    if (iVar5 == 0) goto LAB_7ffa1b03c1d9;
    iVar5 = FUN_7ffa1b0398e0(param_1,plVar1,local_res18 + 0x20,local_res18 + 0x20);
    if (iVar5 != 0) {
      return iVar5;
    }
    iVar5 = FUN_7ffa1b0398e0(param_1,param_4 + 4,plVar1,plVar1);
    if (iVar5 != 0) {
      return iVar5;
    }
    iVar5 = FUN_7ffa1b0398e0(param_1,plVar1,param_4 + 4,param_1 + 0x18);
    if (iVar5 != 0) {
      return iVar5;
    }
    iVar5 = FUN_7ffa1b039b10(param_1,param_4,param_4,plVar1);
  }
  if (iVar5 != 0) {
    return iVar5;
  }
LAB_7ffa1b03c1d9:
  lVar9 = local_res18 + 0x10;
  iVar5 = FUN_7ffa1b0398e0(param_1,param_4 + 4,lVar9,lVar9);
  if (((((iVar5 == 0) && (iVar5 = FUN_7ffa1b039c20(param_1,param_4 + 4), iVar5 == 0)) &&
       (iVar5 = FUN_7ffa1b0398e0(param_1,plVar1,local_res18,param_4 + 4), iVar5 == 0)) &&
      (((iVar5 = FUN_7ffa1b039c20(param_1,plVar1), iVar5 == 0 &&
        (iVar5 = FUN_7ffa1b0398e0(param_1,param_4 + 6,param_4 + 4,param_4 + 4), iVar5 == 0)) &&
       ((iVar5 = FUN_7ffa1b039c20(param_1,param_4 + 6), iVar5 == 0 &&
        ((iVar5 = FUN_7ffa1b0398e0(param_1,param_4 + 4,param_4,param_4), iVar5 == 0 &&
         (iVar5 = FUN_7ffa1b039a60(param_1,param_4 + 4,param_4 + 4,plVar1), iVar5 == 0)))))))) &&
     ((iVar5 = FUN_7ffa1b039a60(param_1,param_4 + 4,param_4 + 4,plVar1), iVar5 == 0 &&
      (((((iVar5 = FUN_7ffa1b039a60(param_1,plVar1,plVar1,param_4 + 4), iVar5 == 0 &&
          (iVar5 = FUN_7ffa1b0398e0(param_1,plVar1,plVar1,param_4), iVar5 == 0)) &&
         (iVar5 = FUN_7ffa1b039a60(param_1,plVar1,plVar1,param_4 + 6), iVar5 == 0)) &&
        ((iVar5 = FUN_7ffa1b0398e0(param_1,param_4 + 6,lVar9,local_res18 + 0x20), iVar5 == 0 &&
         (iVar5 = FUN_7ffa1b039c20(param_1,param_4 + 6), lVar9 = local_res10, iVar5 == 0)))) &&
       ((iVar5 = FUN_7ffa1b045c10(local_res10,param_4 + 4), iVar5 == 0 &&
        (iVar5 = FUN_7ffa1b045c10(lVar9 + 0x10,plVar1), iVar5 == 0)))))))) {
    iVar5 = FUN_7ffa1b045c10(lVar9 + 0x20,param_4 + 6);
  }
  return iVar5;
}



// ==================================================================

/* ===== 0x03abb0  820 行 ===== */
// FUN_7ffa1b03abb0 @ 0x7ffa1b03abb0
// signature: undefined FUN_7ffa1b03abb0()
// ==================================================================

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

ulonglong FUN_7ffa1b03abb0(longlong param_1,longlong *param_2,undefined8 ***param_3)

{
  longlong *plVar1;
  code *pcVar2;
  ulonglong **ppuVar3;
  uint uVar4;
  uint uVar5;
  int iVar6;
  ulonglong uVar7;
  undefined8 *puVar8;
  longlong lVar9;
  longlong *plVar10;
  ulonglong *puVar11;
  undefined8 ***pppuVar12;
  ulonglong uVar13;
  ulonglong ***pppuVar14;
  ulonglong uVar15;
  ulonglong uVar16;
  undefined8 ****ppppuVar17;
  short sVar18;
  undefined8 *puVar19;
  undefined8 *puVar20;
  longlong lVar21;
  undefined1 *puVar22;
  undefined1 *puVar23;
  bool bVar24;
  undefined1 *local_108;
  undefined4 local_100;
  ulonglong ***local_f8;
  undefined4 local_f0;
  undefined8 ***local_e8;
  ulonglong local_e0;
  undefined8 ****local_d8;
  undefined4 local_d0;
  ulonglong local_c8;
  undefined8 ****local_c0;
  undefined4 local_b8;
  undefined8 ****local_b0;
  undefined4 local_a8;
  undefined8 ****local_a0;
  undefined4 local_98;
  undefined8 ****local_90;
  undefined4 local_88;
  undefined8 ****local_80;
  undefined4 local_78;
  undefined8 ****local_70;
  undefined4 local_68;
  undefined8 ****local_60;
  undefined4 local_58;
  
  if (param_3 < (undefined8 ***)0x2) {
    uVar7 = FUN_7ffa1b03a610(param_1,*param_2);
    return uVar7;
  }
  puVar8 = (undefined8 *)_calloc_base(param_3);
  if (puVar8 == (undefined8 *)0x0) {
    return 0xffffb280;
  }
  local_108 = (undefined1 *)0x0;
  local_100 = 1;
  lVar9 = (longlong)puVar8 + 10;
  pppuVar12 = param_3;
  do {
    *(undefined4 *)(lVar9 + -2) = 1;
    *(undefined8 *)(lVar9 + -10) = 0;
    lVar9 = lVar9 + 0x10;
    pppuVar12 = (undefined8 ***)((longlong)pppuVar12 - 1);
  } while (pppuVar12 != (undefined8 ***)0x0);
  uVar4 = FUN_7ffa1b045c10(puVar8,*param_2 + 0x20);
  uVar7 = (ulonglong)uVar4;
  puVar23 = local_108;
  if (uVar4 == 0) {
    pppuVar12 = (undefined8 ***)0x1;
    puVar19 = puVar8;
    do {
      puVar20 = puVar19 + 2;
      uVar4 = FUN_7ffa1b046d10(puVar20,puVar19,param_2[(longlong)pppuVar12] + 0x20);
      uVar7 = (ulonglong)uVar4;
      puVar23 = local_108;
      if (uVar4 != 0) goto LAB_7ffa1b03bae7;
      pcVar2 = *(code **)(param_1 + 0x90);
      if (pcVar2 == (code *)0x0) {
        uVar7 = FUN_7ffa1b048740(puVar20,puVar20,param_1 + 8);
        uVar7 = uVar7 & 0xffffffff;
      }
      else {
        if (*(short *)(puVar19 + 3) < 0) {
          local_f8 = (ulonglong ***)&local_e8;
          local_e8 = (undefined8 ***)0x0;
          local_f0 = 0x10001;
          iVar6 = FUN_7ffa1b046600(puVar20,&local_f8);
          if (iVar6 != 0) goto LAB_7ffa1b03bada;
        }
        uVar7 = FUN_7ffa1b045fd0(puVar20);
        if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar7) goto LAB_7ffa1b03bada;
        uVar4 = (*pcVar2)(puVar20);
        uVar7 = (ulonglong)uVar4;
        if (uVar4 == 0) {
          if (*(short *)(puVar19 + 3) < 0) {
            local_e8 = (undefined8 ***)0x0;
            do {
              local_d8 = &local_e8;
              local_d0 = 0x10001;
              iVar6 = FUN_7ffa1b046600(puVar20,&local_d8);
              if (iVar6 == 0) break;
              uVar4 = FUN_7ffa1b0469c0(puVar20,puVar20,param_1 + 8);
              uVar7 = (ulonglong)uVar4;
              if (uVar4 != 0) goto LAB_7ffa1b03adc7;
            } while (*(short *)(puVar19 + 3) < 0);
          }
          lVar9 = param_1 + 8;
          iVar6 = FUN_7ffa1b046600(puVar20,lVar9);
          while (-1 < iVar6) {
            uVar4 = FUN_7ffa1b046830(puVar20,puVar20,lVar9);
            uVar7 = (ulonglong)uVar4;
            if (uVar4 != 0) break;
            iVar6 = FUN_7ffa1b046600(puVar20,lVar9);
          }
        }
      }
LAB_7ffa1b03adc7:
      puVar23 = local_108;
      if ((int)uVar7 != 0) goto LAB_7ffa1b03bae7;
      _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
      pppuVar12 = (undefined8 ***)((longlong)pppuVar12 + 1);
      puVar19 = puVar20;
    } while (pppuVar12 < param_3);
    plVar1 = (longlong *)(param_1 + 8);
    uVar4 = FUN_7ffa1b048ce0(0,puVar8 + (longlong)param_3 * 2 + -2,
                             puVar8 + (longlong)param_3 * 2 + -2);
    uVar7 = (ulonglong)uVar4;
    puVar23 = local_108;
    pppuVar12 = param_3;
    if (uVar4 == 0) {
      while( true ) {
        pppuVar12 = (undefined8 ***)((longlong)pppuVar12 - 1);
        local_e8 = pppuVar12;
        if (pppuVar12 != (undefined8 ***)0x0) break;
        uVar4 = FUN_7ffa1b045c10(&local_108,puVar8);
        uVar7 = (ulonglong)uVar4;
        puVar23 = local_108;
        if (uVar4 != 0) goto LAB_7ffa1b03bae7;
        lVar9 = 0;
LAB_7ffa1b03b339:
        lVar9 = *(longlong *)(lVar9 + (longlong)param_2);
        lVar21 = lVar9 + 0x10;
        uVar4 = FUN_7ffa1b046d10(lVar21,lVar21,&local_108);
        uVar7 = (ulonglong)uVar4;
        puVar23 = local_108;
        if (uVar4 != 0) goto LAB_7ffa1b03bae7;
        pcVar2 = *(code **)(param_1 + 0x90);
        if (pcVar2 == (code *)0x0) {
          uVar7 = FUN_7ffa1b048740(lVar21,lVar21,plVar1);
          uVar7 = uVar7 & 0xffffffff;
        }
        else {
          if (*(short *)(lVar9 + 0x18) < 0) {
            local_b0 = &local_f8;
            local_f8 = (ulonglong ***)0x0;
            local_a8 = 0x10001;
            iVar6 = FUN_7ffa1b046600(lVar21,&local_b0);
            if (iVar6 != 0) goto LAB_7ffa1b03bada;
          }
          uVar7 = FUN_7ffa1b045fd0(lVar21);
          if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar7) goto LAB_7ffa1b03bada;
          uVar4 = (*pcVar2)(lVar21);
          uVar7 = (ulonglong)uVar4;
          if (uVar4 == 0) {
            if (*(short *)(lVar9 + 0x18) < 0) {
              local_f8 = (ulonglong ***)0x0;
              do {
                local_a0 = &local_f8;
                local_98 = 0x10001;
                iVar6 = FUN_7ffa1b046600(lVar21,&local_a0);
                if (iVar6 == 0) break;
                uVar4 = FUN_7ffa1b0469c0(lVar21,lVar21,plVar1);
                uVar7 = (ulonglong)uVar4;
                if (uVar4 != 0) goto LAB_7ffa1b03b473;
              } while (*(short *)(lVar9 + 0x18) < 0);
            }
            iVar6 = FUN_7ffa1b046600(lVar21,plVar1);
            while (-1 < iVar6) {
              uVar4 = FUN_7ffa1b046830(lVar21,lVar21,plVar1);
              uVar7 = (ulonglong)uVar4;
              if (uVar4 != 0) break;
              iVar6 = FUN_7ffa1b046600(lVar21,plVar1);
            }
          }
        }
LAB_7ffa1b03b473:
        puVar23 = local_108;
        if ((int)uVar7 != 0) goto LAB_7ffa1b03bae7;
        _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
        uVar4 = FUN_7ffa1b046d10(&local_108,&local_108,&local_108);
        uVar7 = (ulonglong)uVar4;
        puVar23 = local_108;
        if (uVar4 != 0) goto LAB_7ffa1b03bae7;
        if (*(longlong *)(param_1 + 0x90) == 0) {
          uVar7 = FUN_7ffa1b048740(&local_108,&local_108,plVar1);
          uVar7 = uVar7 & 0xffffffff;
          puVar23 = local_108;
        }
        else {
          if ((short)local_100 < 0) {
            uVar7 = (ulonglong)local_100._2_2_;
            local_f8 = (ulonglong ***)0x0;
            if (uVar7 != 0) {
              plVar10 = (longlong *)(local_108 + (uVar7 - 1) * 8);
              do {
                if (*plVar10 != 0) break;
                plVar10 = plVar10 + -1;
                uVar7 = uVar7 - 1;
              } while (uVar7 != 0);
            }
            uVar15 = 1;
            ppppuVar17 = &local_f8;
            do {
              if (*ppppuVar17 != (undefined8 ***)0x0) break;
              ppppuVar17 = ppppuVar17 + -1;
              uVar15 = uVar15 - 1;
            } while (uVar15 != 0);
            if (uVar7 == 0) {
              bVar24 = uVar15 == 0;
            }
            else {
              if (uVar7 <= uVar15) goto LAB_7ffa1b03bad3;
              bVar24 = (short)local_100 == 0;
            }
            if (!bVar24) goto LAB_7ffa1b03bad3;
          }
          uVar7 = (ulonglong)local_100._2_2_;
          uVar4 = (uint)local_100._2_2_;
          do {
            uVar7 = uVar7 - 1;
            if ((longlong)uVar7 < 0) {
              uVar15 = 0;
              goto LAB_7ffa1b03b568;
            }
            uVar4 = uVar4 - 1;
          } while (*(ulonglong *)(local_108 + uVar7 * 8) == 0);
          uVar16 = 0x8000000000000000;
          uVar15 = 0;
          do {
            if ((uVar16 & *(ulonglong *)(local_108 + uVar7 * 8)) != 0) break;
            uVar16 = uVar16 >> 1;
            uVar15 = uVar15 + 1;
          } while (uVar15 < 0x40);
          uVar15 = ((longlong)(int)uVar4 + 1) * 0x40 - uVar15;
LAB_7ffa1b03b568:
          if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar15) goto LAB_7ffa1b03bad3;
          uVar4 = (**(code **)(param_1 + 0x90))(&local_108);
          uVar7 = (ulonglong)uVar4;
          if (uVar4 == 0) {
            uVar4 = local_100 & 0xffff;
            if ((short)local_100 < 0) {
              local_c8 = 0;
              do {
                uVar15 = (ulonglong)local_100._2_2_;
                if (uVar15 != 0) {
                  plVar10 = (longlong *)(local_108 + (uVar15 - 1) * 8);
                  do {
                    if (*plVar10 != 0) break;
                    plVar10 = plVar10 + -1;
                    uVar15 = uVar15 - 1;
                  } while (uVar15 != 0);
                }
                puVar11 = &local_c8;
                uVar16 = 1;
                do {
                  if (*puVar11 != 0) break;
                  puVar11 = puVar11 + -1;
                  uVar16 = uVar16 - 1;
                } while (uVar16 != 0);
                sVar18 = (short)uVar4;
                if (uVar15 == 0) {
                  if (uVar16 == 0) break;
LAB_7ffa1b03b605:
                  if ((uVar16 <= uVar15) && (-1 < sVar18)) {
                    if (uVar15 != 0) {
                      puVar11 = (ulonglong *)(local_108 + uVar15 * 8 + -8);
                      while (uVar16 = *(ulonglong *)
                                       (((longlong)&local_c8 - (longlong)local_108) +
                                       (longlong)puVar11), *puVar11 <= uVar16) {
                        if (*puVar11 < uVar16) {
                          iVar6 = -(int)sVar18;
                          goto LAB_7ffa1b03b67b;
                        }
                        puVar11 = puVar11 + -1;
                        uVar15 = uVar15 - 1;
                        if (uVar15 == 0) goto LAB_7ffa1b03b7b1;
                      }
                      goto LAB_7ffa1b03b678;
                    }
                    break;
                  }
                }
                else {
                  if (uVar15 <= uVar16) goto LAB_7ffa1b03b605;
LAB_7ffa1b03b678:
                  iVar6 = (int)sVar18;
LAB_7ffa1b03b67b:
                  if (iVar6 == 0) break;
                }
                uVar4 = (uint)sVar18;
                if ((int)((int)*(short *)(param_1 + 0x10) * uVar4) < 0) {
                  uVar7 = (ulonglong)local_100._2_2_;
                  if (uVar7 != 0) {
                    plVar10 = (longlong *)(local_108 + (uVar7 - 1) * 8);
                    do {
                      if (*plVar10 != 0) break;
                      plVar10 = plVar10 + -1;
                      uVar7 = uVar7 - 1;
                    } while (uVar7 != 0);
                  }
                  uVar15 = (ulonglong)*(ushort *)(param_1 + 0x12);
                  if (uVar15 != 0) {
                    plVar10 = (longlong *)(*plVar1 + uVar15 * 8);
                    do {
                      plVar10 = plVar10 + -1;
                      if (*plVar10 != 0) break;
                      uVar15 = uVar15 - 1;
                    } while (uVar15 != 0);
                  }
                  if (uVar15 < uVar7) {
LAB_7ffa1b03b6ea:
                    bVar24 = true;
                  }
                  else {
                    if (uVar7 < uVar15) {
LAB_7ffa1b03b751:
                      uVar5 = FUN_7ffa1b046830(&local_108,plVar1,&local_108);
                      if (uVar5 != 0) goto LAB_7ffa1b03b792;
                      uVar4 = (uint)(ushort)-sVar18;
                      uVar7 = 0;
                      local_100 = CONCAT22(local_100._2_2_,-sVar18);
                      goto LAB_7ffa1b03b79d;
                    }
                    if (uVar7 != 0) {
                      puVar11 = (ulonglong *)(local_108 + uVar7 * 8 + -8);
                      do {
                        uVar15 = *(ulonglong *)((*plVar1 - (longlong)local_108) + (longlong)puVar11)
                        ;
                        if (uVar15 < *puVar11) goto LAB_7ffa1b03b6ea;
                        if (*puVar11 < uVar15) goto LAB_7ffa1b03b751;
                        puVar11 = puVar11 + -1;
                        uVar7 = uVar7 - 1;
                      } while (uVar7 != 0);
                    }
                    bVar24 = false;
                  }
                  uVar5 = FUN_7ffa1b046830(&local_108,&local_108,plVar1);
                  if (uVar5 != 0) goto LAB_7ffa1b03b792;
                  uVar7 = 0;
                  if (!bVar24) {
                    uVar4 = 1;
                  }
                  local_100 = CONCAT22(local_100._2_2_,(short)uVar4);
                }
                else {
                  uVar5 = FUN_7ffa1b0466e0(&local_108,&local_108,plVar1);
                  if (uVar5 == 0) {
                    local_100 = CONCAT22(local_100._2_2_,sVar18);
                    uVar7 = 0;
                  }
                  else {
LAB_7ffa1b03b792:
                    uVar7 = (ulonglong)uVar5;
                    if (uVar5 != 0) goto LAB_7ffa1b03b7eb;
                    uVar4 = local_100 & 0xffff;
                  }
                }
LAB_7ffa1b03b79d:
              } while ((short)uVar4 < 0);
            }
LAB_7ffa1b03b7b1:
            puVar23 = local_108;
            iVar6 = FUN_7ffa1b046600(&local_108,plVar1);
            if (iVar6 < 0) goto LAB_7ffa1b03b7f4;
            do {
              uVar4 = FUN_7ffa1b046830(&local_108,&local_108,plVar1);
              uVar7 = (ulonglong)uVar4;
              if (uVar4 != 0) break;
              iVar6 = FUN_7ffa1b046600(&local_108,plVar1);
            } while (-1 < iVar6);
          }
LAB_7ffa1b03b7eb:
          puVar23 = local_108;
        }
LAB_7ffa1b03b7f4:
        if ((int)uVar7 != 0) goto LAB_7ffa1b03bae7;
        lVar9 = param_2[(longlong)pppuVar12];
        _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
        uVar4 = FUN_7ffa1b046d10(lVar9,lVar9,&local_108);
        uVar7 = (ulonglong)uVar4;
        puVar23 = local_108;
        if (uVar4 != 0) goto LAB_7ffa1b03bae7;
        pcVar2 = *(code **)(param_1 + 0x90);
        if (pcVar2 == (code *)0x0) {
          uVar7 = FUN_7ffa1b048740(lVar9,lVar9,plVar1);
          uVar7 = uVar7 & 0xffffffff;
        }
        else {
          if (*(short *)(lVar9 + 8) < 0) {
            local_90 = &local_f8;
            local_f8 = (ulonglong ***)0x0;
            local_88 = 0x10001;
            iVar6 = FUN_7ffa1b046600(lVar9,&local_90);
            if (iVar6 != 0) goto LAB_7ffa1b03bada;
          }
          uVar7 = FUN_7ffa1b045fd0(lVar9);
          if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar7) goto LAB_7ffa1b03bada;
          uVar4 = (*pcVar2)(lVar9);
          uVar7 = (ulonglong)uVar4;
          if (uVar4 == 0) {
            if (*(short *)(lVar9 + 8) < 0) {
              local_f8 = (ulonglong ***)0x0;
              do {
                local_80 = &local_f8;
                local_78 = 0x10001;
                iVar6 = FUN_7ffa1b046600(lVar9,&local_80);
                if (iVar6 == 0) break;
                uVar4 = FUN_7ffa1b0469c0(lVar9,lVar9,plVar1);
                uVar7 = (ulonglong)uVar4;
                if (uVar4 != 0) goto LAB_7ffa1b03b933;
              } while (*(short *)(lVar9 + 8) < 0);
            }
            iVar6 = FUN_7ffa1b046600(lVar9,plVar1);
            while (-1 < iVar6) {
              uVar4 = FUN_7ffa1b046830(lVar9,lVar9,plVar1);
              uVar7 = (ulonglong)uVar4;
              if (uVar4 != 0) break;
              iVar6 = FUN_7ffa1b046600(lVar9,plVar1);
            }
          }
        }
LAB_7ffa1b03b933:
        puVar23 = local_108;
        if ((int)uVar7 != 0) goto LAB_7ffa1b03bae7;
        lVar9 = param_2[(longlong)pppuVar12];
        _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
        lVar21 = lVar9 + 0x10;
        uVar4 = FUN_7ffa1b046d10(lVar21,lVar21,&local_108);
        uVar7 = (ulonglong)uVar4;
        puVar23 = local_108;
        if (uVar4 != 0) goto LAB_7ffa1b03bae7;
        pcVar2 = *(code **)(param_1 + 0x90);
        if (pcVar2 == (code *)0x0) {
          uVar7 = FUN_7ffa1b048740(lVar21,lVar21,plVar1);
          uVar7 = uVar7 & 0xffffffff;
        }
        else {
          if (*(short *)(lVar9 + 0x18) < 0) {
            local_70 = &local_f8;
            local_f8 = (ulonglong ***)0x0;
            local_68 = 0x10001;
            iVar6 = FUN_7ffa1b046600(lVar21,&local_70);
            if (iVar6 != 0) goto LAB_7ffa1b03bada;
          }
          uVar7 = FUN_7ffa1b045fd0(lVar21);
          if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar7) goto LAB_7ffa1b03bada;
          uVar4 = (*pcVar2)(lVar21);
          uVar7 = (ulonglong)uVar4;
          if (uVar4 == 0) {
            if (*(short *)(lVar9 + 0x18) < 0) {
              local_f8 = (ulonglong ***)0x0;
              do {
                local_60 = &local_f8;
                local_58 = 0x10001;
                iVar6 = FUN_7ffa1b046600(lVar21,&local_60);
                if (iVar6 == 0) break;
                uVar4 = FUN_7ffa1b0469c0(lVar21,lVar21,plVar1);
                uVar7 = (ulonglong)uVar4;
                if (uVar4 != 0) goto LAB_7ffa1b03ba73;
              } while (*(short *)(lVar9 + 0x18) < 0);
            }
            iVar6 = FUN_7ffa1b046600(lVar21,plVar1);
            while (-1 < iVar6) {
              uVar4 = FUN_7ffa1b046830(lVar21,lVar21,plVar1);
              uVar7 = (ulonglong)uVar4;
              if (uVar4 != 0) break;
              iVar6 = FUN_7ffa1b046600(lVar21,plVar1);
            }
          }
        }
LAB_7ffa1b03ba73:
        puVar23 = local_108;
        if ((int)uVar7 != 0) goto LAB_7ffa1b03bae7;
        _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
        uVar4 = FUN_7ffa1b0459c0(param_2[(longlong)pppuVar12],*(undefined2 *)(param_1 + 0x12));
        uVar7 = (ulonglong)uVar4;
        puVar23 = local_108;
        if (uVar4 != 0) goto LAB_7ffa1b03bae7;
        uVar4 = FUN_7ffa1b0459c0(param_2[(longlong)pppuVar12] + 0x10,*(undefined2 *)(param_1 + 0x12)
                                );
        uVar7 = (ulonglong)uVar4;
        puVar23 = local_108;
        if (uVar4 != 0) goto LAB_7ffa1b03bae7;
        uVar4 = FUN_7ffa1b045d10(param_2[(longlong)pppuVar12] + 0x20,1);
        uVar7 = (ulonglong)uVar4;
        puVar23 = local_108;
        if ((uVar4 != 0) || (pppuVar12 == (undefined8 ***)0x0)) goto LAB_7ffa1b03bae7;
      }
      puVar19 = puVar8 + (longlong)pppuVar12 * 2;
      uVar4 = FUN_7ffa1b046d10(&local_108,puVar19,puVar19 + -2);
      uVar7 = (ulonglong)uVar4;
      puVar23 = local_108;
      if (uVar4 == 0) {
        if (*(code **)(param_1 + 0x90) == (code *)0x0) {
          uVar7 = FUN_7ffa1b048740(&local_108,&local_108,plVar1);
          uVar7 = uVar7 & 0xffffffff;
          goto LAB_7ffa1b03b19c;
        }
        if ((short)local_100 < 0) {
          uVar7 = (ulonglong)local_100._2_2_;
          local_f8 = (ulonglong ***)0x0;
          if (uVar7 != 0) {
            plVar10 = (longlong *)(local_108 + (uVar7 - 1) * 8);
            do {
              if (*plVar10 != 0) break;
              plVar10 = plVar10 + -1;
              uVar7 = uVar7 - 1;
            } while (uVar7 != 0);
          }
          uVar15 = 1;
          ppppuVar17 = &local_f8;
          do {
            if (*ppppuVar17 != (undefined8 ***)0x0) break;
            ppppuVar17 = ppppuVar17 + -1;
            uVar15 = uVar15 - 1;
          } while (uVar15 != 0);
          if (uVar7 == 0) {
            bVar24 = uVar15 == 0;
LAB_7ffa1b03aed5:
            if (bVar24) goto LAB_7ffa1b03aedb;
          }
          else if (uVar15 < uVar7) {
            bVar24 = (short)local_100 == 0;
            goto LAB_7ffa1b03aed5;
          }
        }
        else {
LAB_7ffa1b03aedb:
          uVar7 = (ulonglong)local_100._2_2_;
          uVar4 = (uint)local_100._2_2_;
          do {
            uVar7 = uVar7 - 1;
            if ((longlong)uVar7 < 0) {
              uVar15 = 0;
              goto LAB_7ffa1b03af08;
            }
            uVar4 = uVar4 - 1;
          } while (*(ulonglong *)(local_108 + uVar7 * 8) == 0);
          uVar16 = 0x8000000000000000;
          uVar15 = 0;
          do {
            if ((uVar16 & *(ulonglong *)(local_108 + uVar7 * 8)) != 0) break;
            uVar16 = uVar16 >> 1;
            uVar15 = uVar15 + 1;
          } while (uVar15 < 0x40);
          uVar15 = ((longlong)(int)uVar4 + 1) * 0x40 - uVar15;
LAB_7ffa1b03af08:
          if (uVar15 <= (ulonglong)(*(longlong *)(param_1 + 0x78) * 2)) {
            uVar4 = (**(code **)(param_1 + 0x90))(&local_108);
            uVar7 = (ulonglong)uVar4;
            if (uVar4 == 0) {
              uVar4 = local_100 & 0xffff;
              if ((short)local_100 < 0) {
                local_e0 = 0;
                do {
                  uVar16 = (ulonglong)local_100._2_2_;
                  uVar15 = uVar16;
                  if (uVar16 != 0) {
                    plVar10 = (longlong *)(local_108 + uVar16 * 8 + -8);
                    do {
                      if (*plVar10 != 0) break;
                      plVar10 = plVar10 + -1;
                      uVar15 = uVar15 - 1;
                    } while (uVar15 != 0);
                  }
                  puVar11 = &local_e0;
                  uVar13 = 1;
                  do {
                    if (*puVar11 != 0) break;
                    puVar11 = puVar11 + -1;
                    uVar13 = uVar13 - 1;
                  } while (uVar13 != 0);
                  sVar18 = (short)uVar4;
                  if (uVar15 == 0) {
                    if (uVar13 == 0) break;
LAB_7ffa1b03afa4:
                    if ((uVar13 <= uVar15) && (-1 < sVar18)) {
                      if (uVar15 != 0) {
                        pppuVar14 = (ulonglong ***)(&local_e8 + uVar15);
                        while (ppuVar3 = *(ulonglong ***)
                                          (((longlong)local_108 - (longlong)&local_e0) +
                                          (longlong)pppuVar14), ppuVar3 <= *pppuVar14) {
                          if (ppuVar3 < *pppuVar14) {
                            iVar6 = -(int)sVar18;
                            goto LAB_7ffa1b03b037;
                          }
                          pppuVar14 = pppuVar14 + -1;
                          uVar15 = uVar15 - 1;
                          if (uVar15 == 0) goto LAB_7ffa1b03b162;
                        }
                        goto LAB_7ffa1b03b034;
                      }
                      break;
                    }
                  }
                  else {
                    if (uVar15 <= uVar13) goto LAB_7ffa1b03afa4;
LAB_7ffa1b03b034:
                    iVar6 = (int)sVar18;
LAB_7ffa1b03b037:
                    if (iVar6 == 0) break;
                  }
                  uVar4 = (uint)sVar18;
                  if ((int)((int)*(short *)(param_1 + 0x10) * uVar4) < 0) {
                    if (uVar16 != 0) {
                      plVar10 = (longlong *)(local_108 + (uVar16 - 1) * 8);
                      do {
                        if (*plVar10 != 0) break;
                        plVar10 = plVar10 + -1;
                        uVar16 = uVar16 - 1;
                      } while (uVar16 != 0);
                    }
                    uVar7 = (ulonglong)*(ushort *)(param_1 + 0x12);
                    if (uVar7 != 0) {
                      plVar10 = (longlong *)(*plVar1 + (uVar7 - 1) * 8);
                      do {
                        if (*plVar10 != 0) break;
                        plVar10 = plVar10 + -1;
                        uVar7 = uVar7 - 1;
                      } while (uVar7 != 0);
                    }
                    if (uVar7 < uVar16) {
LAB_7ffa1b03b0a5:
                      bVar24 = true;
                    }
                    else {
                      if (uVar16 < uVar7) {
LAB_7ffa1b03b102:
                        uVar5 = FUN_7ffa1b046830(&local_108,plVar1,&local_108);
                        if (uVar5 != 0) goto LAB_7ffa1b03b143;
                        uVar4 = (uint)(ushort)-sVar18;
                        uVar7 = 0;
                        local_100 = CONCAT22(local_100._2_2_,-sVar18);
                        goto LAB_7ffa1b03b14e;
                      }
                      if (uVar16 != 0) {
                        puVar11 = (ulonglong *)(local_108 + uVar16 * 8 + -8);
                        do {
                          uVar7 = *(ulonglong *)
                                   ((*plVar1 - (longlong)local_108) + (longlong)puVar11);
                          if (uVar7 < *puVar11) goto LAB_7ffa1b03b0a5;
                          if (*puVar11 < uVar7) goto LAB_7ffa1b03b102;
                          puVar11 = puVar11 + -1;
                          uVar16 = uVar16 - 1;
                        } while (uVar16 != 0);
                      }
                      bVar24 = false;
                    }
                    uVar5 = FUN_7ffa1b046830(&local_108,&local_108,plVar1);
                    if (uVar5 != 0) goto LAB_7ffa1b03b143;
                    uVar7 = 0;
                    if (!bVar24) {
                      uVar4 = 1;
                    }
                    local_100 = CONCAT22(local_100._2_2_,(short)uVar4);
                  }
                  else {
                    uVar5 = FUN_7ffa1b0466e0(&local_108,&local_108,plVar1);
                    if (uVar5 == 0) {
                      local_100 = CONCAT22(local_100._2_2_,sVar18);
                      uVar7 = 0;
                    }
                    else {
LAB_7ffa1b03b143:
                      uVar7 = (ulonglong)uVar5;
                      if (uVar5 != 0) goto LAB_7ffa1b03b19c;
                      uVar4 = local_100 & 0xffff;
                    }
                  }
LAB_7ffa1b03b14e:
                } while ((short)uVar4 < 0);
              }
LAB_7ffa1b03b162:
              puVar23 = local_108;
              iVar6 = FUN_7ffa1b046600(&local_108,plVar1);
              if (-1 < iVar6) {
                do {
                  uVar4 = FUN_7ffa1b046830(&local_108,&local_108,plVar1);
                  uVar7 = (ulonglong)uVar4;
                  if (uVar4 != 0) break;
                  iVar6 = FUN_7ffa1b046600(&local_108,plVar1);
                } while (-1 < iVar6);
                goto LAB_7ffa1b03b19c;
              }
            }
            else {
LAB_7ffa1b03b19c:
              puVar23 = local_108;
            }
            if ((int)uVar7 == 0) {
              lVar9 = (longlong)local_e8 * 8;
              _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
              uVar4 = FUN_7ffa1b046d10(puVar19 + -2,puVar19,param_2[(longlong)local_e8] + 0x20);
              uVar7 = (ulonglong)uVar4;
              puVar23 = local_108;
              if (uVar4 == 0) {
                pcVar2 = *(code **)(param_1 + 0x90);
                if (pcVar2 == (code *)0x0) {
                  uVar7 = FUN_7ffa1b048740(puVar19 + -2,puVar19 + -2,plVar1);
                  uVar7 = uVar7 & 0xffffffff;
                }
                else {
                  if (*(short *)(puVar19 + -1) < 0) {
                    local_d8 = &local_f8;
                    local_f8 = (ulonglong ***)0x0;
                    local_d0 = 0x10001;
                    iVar6 = FUN_7ffa1b046600(puVar19 + -2,&local_d8);
                    if (iVar6 != 0) goto LAB_7ffa1b03bada;
                  }
                  uVar7 = FUN_7ffa1b045fd0(puVar19 + -2);
                  if ((ulonglong)(*(longlong *)(param_1 + 0x78) * 2) < uVar7) goto LAB_7ffa1b03bada;
                  uVar4 = (*pcVar2)(puVar19 + -2);
                  uVar7 = (ulonglong)uVar4;
                  if (uVar4 == 0) {
                    if (*(short *)(puVar19 + -1) < 0) {
                      local_f8 = (ulonglong ***)0x0;
                      do {
                        local_c0 = &local_f8;
                        local_b8 = 0x10001;
                        iVar6 = FUN_7ffa1b046600(puVar19 + -2,&local_c0);
                        if (iVar6 == 0) break;
                        uVar4 = FUN_7ffa1b0469c0(puVar19 + -2,puVar19 + -2,plVar1);
                        uVar7 = (ulonglong)uVar4;
                        if (uVar4 != 0) goto LAB_7ffa1b03b306;
                      } while (*(short *)(puVar19 + -1) < 0);
                    }
                    iVar6 = FUN_7ffa1b046600(puVar19 + -2,plVar1);
                    while (-1 < iVar6) {
                      uVar4 = FUN_7ffa1b046830(puVar19 + -2,puVar19 + -2,plVar1);
                      uVar7 = (ulonglong)uVar4;
                      if (uVar4 != 0) break;
                      iVar6 = FUN_7ffa1b046600(puVar19 + -2,plVar1);
                    }
                  }
                }
LAB_7ffa1b03b306:
                puVar23 = local_108;
                if ((int)uVar7 == 0) {
                  _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
                  pppuVar12 = local_e8;
                  goto LAB_7ffa1b03b339;
                }
              }
            }
            goto LAB_7ffa1b03bae7;
          }
        }
LAB_7ffa1b03bad3:
        uVar7 = 0xffffb080;
        puVar23 = local_108;
      }
    }
  }
LAB_7ffa1b03bae7:
  if (puVar23 != (undefined1 *)0x0) {
    lVar9 = (ulonglong)local_100._2_2_ << 3;
    if ((ulonglong)local_100._2_2_ != 0) {
      puVar22 = puVar23;
      for (; lVar9 != 0; lVar9 = lVar9 + -1) {
        *puVar22 = 0;
        puVar22 = puVar22 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar23);
  }
  local_100 = 1;
  local_108 = (undefined1 *)0x0;
  puVar19 = puVar8;
  do {
    param_3 = (undefined8 ***)((longlong)param_3 - 1);
    if (puVar19 != (undefined8 *)0x0) {
      puVar23 = (undefined1 *)*puVar19;
      if (puVar23 != (undefined1 *)0x0) {
        lVar9 = (ulonglong)*(ushort *)((longlong)puVar19 + 10) << 3;
        if ((ulonglong)*(ushort *)((longlong)puVar19 + 10) != 0) {
          puVar22 = puVar23;
          for (; lVar9 != 0; lVar9 = lVar9 + -1) {
            *puVar22 = 0;
            puVar22 = puVar22 + 1;
          }
        }
        thunk_FUN_7ffa1b0c8950(puVar23);
      }
      *(undefined4 *)(puVar19 + 1) = 1;
      *puVar19 = 0;
    }
    puVar19 = puVar19 + 2;
  } while (param_3 != (undefined8 ***)0x0);
  thunk_FUN_7ffa1b0c8950(puVar8);
  return uVar7;
LAB_7ffa1b03bada:
  uVar7 = 0xffffb080;
  puVar23 = local_108;
  goto LAB_7ffa1b03bae7;
}



// ==================================================================

/* ===== 0x03c3e0  138 行 ===== */
// FUN_7ffa1b03c3e0 @ 0x7ffa1b03c3e0
// signature: undefined FUN_7ffa1b03c3e0()
// ==================================================================

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined8
FUN_7ffa1b03c3e0(undefined8 param_1,longlong param_2,longlong param_3,longlong param_4,
                longlong param_5)

{
  int iVar1;
  undefined8 uVar2;
  undefined8 local_res10;
  undefined8 *local_38;
  undefined4 local_30;
  
  _DAT_7ffa1b3a18ac = _DAT_7ffa1b3a18ac + 1;
  if (*(longlong *)(param_4 + 0x20) != 0) {
    local_38 = &local_res10;
    local_res10 = 0;
    local_30 = 0x10001;
    iVar1 = FUN_7ffa1b046600(param_3 + 0x20,&local_38);
    if (iVar1 == 0) {
      uVar2 = FUN_7ffa1b039390(param_2,param_4);
      return uVar2;
    }
    local_38 = &local_res10;
    local_res10 = 0;
    local_30 = 0x10001;
    iVar1 = FUN_7ffa1b046600(param_4 + 0x20,&local_38);
    if (iVar1 == 0) {
      uVar2 = FUN_7ffa1b039390(param_2,param_3);
      return uVar2;
    }
    local_38 = &local_res10;
    local_res10 = 1;
    local_30 = 0x10001;
    iVar1 = FUN_7ffa1b046600(param_4 + 0x20,&local_38);
    if (iVar1 == 0) {
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5,param_3 + 0x20,param_3 + 0x20);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5 + 0x10,param_5,param_3 + 0x20);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5,param_5,param_4);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5 + 0x10,param_5 + 0x10,param_4 + 0x10);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b039a60(param_1,param_5,param_5,param_3);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b039a60(param_1,param_5 + 0x10,param_5 + 0x10,param_3 + 0x10);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      local_38 = &local_res10;
      local_res10 = 0;
      local_30 = 0x10001;
      iVar1 = FUN_7ffa1b046600(param_5,&local_38);
      if (iVar1 == 0) {
        local_38 = &local_res10;
        local_res10 = 0;
        local_30 = 0x10001;
        iVar1 = FUN_7ffa1b046600(param_5 + 0x10,&local_38);
        if (iVar1 == 0) {
          uVar2 = FUN_7ffa1b03bd10(param_1,param_2,param_3,param_5);
          return uVar2;
        }
        uVar2 = FUN_7ffa1b039490(param_2);
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_2 + 0x20,param_3 + 0x20,param_5);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5 + 0x20,param_5,param_5);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5 + 0x30,param_5 + 0x20,param_5);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5 + 0x20,param_5 + 0x20,param_3);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b045c10(param_5,param_5 + 0x20);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b039c20(param_1,param_5);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_2,param_5 + 0x10,param_5 + 0x10);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b039a60(param_1,param_2,param_2,param_5);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b039a60(param_1,param_2,param_2,param_5 + 0x30);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b039a60(param_1,param_5 + 0x20,param_5 + 0x20,param_2);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5 + 0x20,param_5 + 0x20,param_5 + 0x10);
      if ((int)uVar2 != 0) {
        return uVar2;
      }
      uVar2 = FUN_7ffa1b0398e0(param_1,param_5 + 0x30,param_5 + 0x30,param_3 + 0x10);
      if ((int)uVar2 == 0) {
        uVar2 = FUN_7ffa1b039a60(param_1,param_2 + 0x10,param_5 + 0x20,param_5 + 0x30);
        return uVar2;
      }
      return uVar2;
    }
  }
  return 0xffffb080;
}



// ==================================================================

/* ===== 0x03dce0  258 行 ===== */
// FUN_7ffa1b03dce0 @ 0x7ffa1b03dce0
// signature: undefined FUN_7ffa1b03dce0()
// ==================================================================

int FUN_7ffa1b03dce0(longlong param_1,longlong *param_2,byte *param_3,ulonglong param_4,byte param_5
                    ,byte *param_6)

{
  undefined1 auVar1 [16];
  ushort uVar2;
  byte bVar3;
  int iVar4;
  ulonglong *puVar5;
  byte bVar6;
  longlong lVar7;
  ulonglong uVar8;
  ulonglong *puVar9;
  longlong *plVar10;
  ulonglong uVar11;
  ushort uVar12;
  ulonglong uVar13;
  ulonglong *puVar14;
  byte bVar15;
  byte bVar16;
  longlong *plVar17;
  ulonglong uVar18;
  char cVar19;
  byte *pbVar20;
  uint uVar21;
  uint uVar22;
  ulonglong *local_48;
  undefined4 local_40;
  longlong local_38 [2];
  
  plVar17 = (longlong *)(param_1 + 0x68);
  local_40 = 1;
  local_48 = (ulonglong *)0x0;
  uVar12 = 0;
  puVar9 = (ulonglong *)0x0;
  uVar13 = 0;
  if ((*(short *)(param_1 + 0x72) == 0) || ((*(byte *)*plVar17 & 1) == 0)) {
    return -0x4f80;
  }
  uVar2 = *(ushort *)((longlong)param_2 + 10);
  if ((ulonglong)uVar2 == 0) {
    bVar15 = 0;
  }
  else {
    bVar15 = (byte)*(undefined4 *)*param_2 & 1;
  }
  *param_6 = bVar15 ^ 1;
  if ((local_38 == param_2) || (uVar2 == 0)) {
LAB_7ffa1b03de0e:
    if (-((int)*(short *)(param_1 + 0x70) * (int)(short)param_2[1]) < 0) {
      iVar4 = FUN_7ffa1b046560(plVar17,param_2);
      if (iVar4 < 0) {
        plVar10 = param_2;
      }
      else {
        plVar10 = plVar17;
        plVar17 = param_2;
      }
      iVar4 = FUN_7ffa1b046830(&local_48,plVar10,plVar17);
      if (iVar4 != 0) goto LAB_7ffa1b03de61;
LAB_7ffa1b03de66:
      uVar2 = local_40._2_2_;
      uVar13 = (ulonglong)local_40._2_2_;
      bVar15 = *param_6;
      if (10000 < uVar13) {
        iVar4 = -0x10;
        puVar14 = local_48;
        goto LAB_7ffa1b03debd;
      }
      uVar11 = (ulonglong)uVar12;
      puVar5 = puVar9;
      if (uVar11 < uVar13) {
        puVar5 = (ulonglong *)_calloc_base(uVar13,8);
        if (puVar5 == (ulonglong *)0x0) {
          iVar4 = -0x10;
          goto LAB_7ffa1b03deb2;
        }
        if (puVar9 != (ulonglong *)0x0) {
          lVar7 = uVar11 * 8;
          FUN_7ffa1b2ecc80(puVar5,puVar9,lVar7);
          if (uVar11 != 0) {
            puVar14 = puVar9;
            for (; lVar7 != 0; lVar7 = lVar7 + -1) {
              *(undefined1 *)puVar14 = 0;
              puVar14 = (ulonglong *)((longlong)puVar14 + 1);
            }
          }
          thunk_FUN_7ffa1b0c8950(puVar9);
        }
        uVar12 = uVar2;
      }
      puVar14 = local_48;
      iVar4 = 0;
      uVar11 = (longlong)(-((DAT_7ffa1b398920 ^ bVar15) >> 1) | -(DAT_7ffa1b398920 ^ bVar15)) >>
               0x3f;
      if ((puVar5 != local_48) && (uVar13 != 0)) {
        puVar9 = puVar5;
        uVar18 = uVar13;
        do {
          *puVar9 = *(ulonglong *)(((longlong)local_48 - (longlong)puVar5) + (longlong)puVar9) &
                    uVar11 | ~(DAT_7ffa1b398920 ^ uVar11) & *puVar9;
          uVar18 = uVar18 - 1;
          puVar9 = puVar9 + 1;
        } while (uVar18 != 0);
      }
      uVar18 = (ulonglong)uVar12;
      uVar11 = ~uVar11;
      uVar8 = (uint)uVar12 - uVar13;
      if (uVar13 < uVar18) {
        if (7 < uVar8) {
          puVar9 = puVar5 + uVar13 + 4;
          do {
            uVar13 = uVar13 + 8;
            uVar21 = (uint)uVar11;
            uVar22 = (uint)(uVar11 >> 0x20);
            *(uint *)(puVar9 + -4) = uVar21 & (uint)puVar9[-4];
            *(uint *)((longlong)puVar9 + -0x1c) = uVar22 & *(uint *)((longlong)puVar9 + -0x1c);
            *(uint *)(puVar9 + -3) = uVar21 & (uint)puVar9[-3];
            *(uint *)((longlong)puVar9 + -0x14) = uVar22 & *(uint *)((longlong)puVar9 + -0x14);
            *(uint *)(puVar9 + -2) = uVar21 & (uint)puVar9[-2];
            *(uint *)((longlong)puVar9 + -0xc) = uVar22 & *(uint *)((longlong)puVar9 + -0xc);
            *(uint *)(puVar9 + -1) = uVar21 & (uint)puVar9[-1];
            *(uint *)((longlong)puVar9 + -4) = uVar22 & *(uint *)((longlong)puVar9 + -4);
            *(uint *)puVar9 = uVar21 & (uint)*puVar9;
            *(uint *)((longlong)puVar9 + 4) = uVar22 & *(uint *)((longlong)puVar9 + 4);
            *(uint *)(puVar9 + 1) = uVar21 & (uint)puVar9[1];
            *(uint *)((longlong)puVar9 + 0xc) = uVar22 & *(uint *)((longlong)puVar9 + 0xc);
            auVar1 = *(undefined1 (*) [16])(puVar9 + 2);
            *(uint *)(puVar9 + 2) = uVar21 & auVar1._0_4_;
            *(uint *)((longlong)puVar9 + 0x14) = uVar22 & auVar1._4_4_;
            *(uint *)(puVar9 + 3) = uVar21 & auVar1._8_4_;
            *(uint *)((longlong)puVar9 + 0x1c) = uVar22 & auVar1._12_4_;
            puVar9 = puVar9 + 8;
          } while (uVar13 < (ulonglong)(uint)uVar12 - (ulonglong)((uint)uVar8 & 7));
          if (uVar18 <= uVar13) goto LAB_7ffa1b03e06c;
        }
        do {
          puVar5[uVar13] = puVar5[uVar13] & uVar11;
          uVar13 = uVar13 + 1;
        } while (uVar13 < uVar18);
      }
LAB_7ffa1b03e06c:
      FUN_7ffa1b2ec8c0(param_3,0,param_4 + 1);
      uVar13 = 0;
      if (param_4 != 0) {
        do {
          uVar11 = 0;
          if ((ulonglong)param_5 != 0) {
            bVar15 = param_3[uVar13];
            uVar18 = uVar13;
            do {
              if (uVar18 < (ulonglong)uVar12 * 0x40) {
                bVar3 = (byte)(puVar5[uVar18 >> 6] >> ((byte)uVar18 & 0x3f)) & 1;
              }
              else {
                bVar3 = 0;
              }
              uVar18 = uVar18 + param_4;
              bVar6 = (byte)uVar11;
              uVar11 = uVar11 + 1;
              bVar15 = bVar15 | bVar3 << (bVar6 & 0x1f);
            } while (uVar11 < param_5);
            param_3[uVar13] = bVar15;
          }
          uVar13 = uVar13 + 1;
        } while (uVar13 < param_4);
      }
      bVar15 = 0;
      if (param_4 != 0) {
        do {
          pbVar20 = param_3 + 1;
          bVar3 = *pbVar20;
          bVar16 = bVar3 ^ bVar15;
          cVar19 = '\x01' - (bVar16 & 1);
          bVar6 = cVar19 * *param_3;
          *param_3 = cVar19 * -0x80 | *param_3;
          *pbVar20 = bVar6 ^ bVar16;
          bVar15 = bVar6 & bVar16 | bVar3 & bVar15;
          param_4 = param_4 - 1;
          param_3 = pbVar20;
        } while (param_4 != 0);
      }
    }
    else {
      iVar4 = FUN_7ffa1b0466e0(&local_48,plVar17,param_2);
LAB_7ffa1b03de61:
      if (iVar4 == 0) goto LAB_7ffa1b03de66;
LAB_7ffa1b03deb2:
      puVar5 = puVar9;
      puVar14 = local_48;
    }
  }
  else {
    lVar7 = (ulonglong)uVar2 - 1;
    if (lVar7 != 0) {
      plVar10 = (longlong *)(*param_2 + lVar7 * 8);
      do {
        if (*plVar10 != 0) break;
        plVar10 = plVar10 + -1;
        lVar7 = lVar7 + -1;
      } while (lVar7 != 0);
    }
    uVar11 = lVar7 + 1;
    if (uVar11 == 0) {
      FUN_7ffa1b2ec8c0(0,0,0);
LAB_7ffa1b03de00:
      FUN_7ffa1b2ecc80(puVar9,*param_2,uVar11 * 8);
      goto LAB_7ffa1b03de0e;
    }
    puVar14 = (ulonglong *)0x0;
    if (10000 < uVar11) {
      iVar4 = -0x10;
      goto LAB_7ffa1b03debd;
    }
    puVar5 = (ulonglong *)_calloc_base(uVar11,8);
    if (puVar5 != (ulonglong *)0x0) {
      uVar12 = (ushort)uVar11;
      puVar9 = puVar5;
      goto LAB_7ffa1b03de00;
    }
    iVar4 = -0x10;
    puVar5 = puVar9;
  }
  uVar13 = (ulonglong)local_40._2_2_;
  puVar9 = puVar5;
LAB_7ffa1b03debd:
  if (puVar14 != (ulonglong *)0x0) {
    lVar7 = uVar13 << 3;
    if (uVar13 != 0) {
      puVar5 = puVar14;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *(undefined1 *)puVar5 = 0;
        puVar5 = (ulonglong *)((longlong)puVar5 + 1);
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar14);
  }
  if (puVar9 != (ulonglong *)0x0) {
    lVar7 = (ulonglong)uVar12 * 8;
    if ((ulonglong)uVar12 != 0) {
      puVar14 = puVar9;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *(undefined1 *)puVar14 = 0;
        puVar14 = (ulonglong *)((longlong)puVar14 + 1);
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar9);
  }
  return iVar4;
}



// ==================================================================

/* ===== 0x03d2e0  392 行 ===== */
// FUN_7ffa1b03d2e0 @ 0x7ffa1b03d2e0
// signature: undefined FUN_7ffa1b03d2e0()
// ==================================================================

/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

int FUN_7ffa1b03d2e0(longlong param_1,undefined1 **param_2,undefined8 param_3,undefined1 param_4,
                    longlong param_5,longlong param_6,longlong param_7,undefined8 param_8)

{
  undefined1 **ppuVar1;
  undefined1 **ppuVar2;
  ulonglong uVar3;
  ulonglong uVar4;
  int iVar5;
  int iVar6;
  longlong lVar7;
  undefined1 *puVar8;
  undefined1 *puVar9;
  undefined1 *puVar10;
  undefined1 auStack_198 [32];
  undefined1 local_178;
  undefined8 local_168;
  undefined1 local_160;
  undefined1 *local_158;
  undefined4 local_150;
  undefined1 *local_148;
  undefined4 local_140;
  undefined1 *local_138;
  undefined4 local_130;
  undefined8 local_128;
  undefined8 *local_120;
  undefined4 local_118;
  undefined8 *local_110;
  undefined4 local_108;
  undefined8 *local_100;
  undefined4 local_f8;
  undefined8 *local_f0;
  undefined4 local_e8;
  undefined8 *local_e0;
  undefined4 local_d8;
  undefined8 *local_d0;
  undefined4 local_c8;
  undefined8 *local_c0;
  undefined4 local_b8;
  undefined8 *local_b0;
  undefined4 local_a8;
  undefined8 *local_a0;
  undefined4 local_98;
  undefined1 *local_88;
  undefined4 local_80;
  undefined1 *local_78;
  undefined4 local_70;
  undefined1 *local_68;
  undefined4 local_60;
  undefined1 *local_58;
  undefined4 local_50;
  ulonglong local_48;
  
  local_48 = DAT_7ffa1b381040 ^ (ulonglong)auStack_198;
  puVar9 = (undefined1 *)0x0;
  local_158 = (undefined1 *)0x0;
  puVar10 = (undefined1 *)0x0;
  local_148 = (undefined1 *)0x0;
  local_138 = (undefined1 *)0x0;
  local_88 = (undefined1 *)0x0;
  local_78 = (undefined1 *)0x0;
  local_68 = (undefined1 *)0x0;
  local_58 = (undefined1 *)0x0;
  local_150 = 1;
  local_178 = *(undefined1 *)(param_5 + param_6);
  local_140 = 1;
  local_130 = 1;
  local_80 = 1;
  local_70 = 1;
  local_60 = 1;
  local_50 = 1;
  local_160 = param_4;
  local_128 = param_3;
  iVar5 = FUN_7ffa1b03d200(param_1);
  if ((iVar5 == 0) &&
     (((param_7 == 0 || (iVar5 = FUN_7ffa1b03c730(param_1,param_2,param_7,param_8), iVar5 == 0)) &&
      (param_6 != 0)))) {
    while( true ) {
      param_6 = param_6 + -1;
      iVar5 = FUN_7ffa1b03bd10(param_1,param_2,param_2,&local_88);
      if (iVar5 != 0) break;
      local_178 = *(undefined1 *)(param_5 + param_6);
      iVar5 = FUN_7ffa1b03d200(param_1,&local_158,local_128,local_160);
      puVar10 = local_138;
      if (iVar5 != 0) break;
      _DAT_7ffa1b3a18ac = _DAT_7ffa1b3a18ac + 1;
      ppuVar1 = param_2 + 2;
      ppuVar2 = param_2 + 4;
      if (local_138 == (undefined1 *)0x0) {
LAB_7ffa1b03db85:
        iVar5 = -0x4f80;
        break;
      }
      local_120 = &local_168;
      local_118 = 0x10001;
      local_168 = 0;
      iVar5 = FUN_7ffa1b046600(ppuVar2,&local_120);
      if (iVar5 == 0) {
        if (param_2 != &local_158) {
          uVar3 = (ulonglong)local_150._2_2_;
          if (local_150._2_2_ == 0) {
            if (*(ushort *)((longlong)param_2 + 10) != 0) {
              *(undefined2 *)(param_2 + 1) = 1;
              FUN_7ffa1b2ec8c0(*param_2,0,(ulonglong)*(ushort *)((longlong)param_2 + 10) << 3);
            }
          }
          else {
            do {
              uVar4 = uVar3;
              uVar3 = uVar4 - 1;
              if (uVar3 == 0) break;
            } while (*(longlong *)(local_158 + uVar3 * 8) == 0);
            *(undefined2 *)(param_2 + 1) = (undefined2)local_150;
            if (*(ushort *)((longlong)param_2 + 10) < uVar4) {
              iVar5 = FUN_7ffa1b045900(param_2,uVar4);
              if (iVar5 != 0) goto LAB_7ffa1b03db6f;
            }
            else {
              FUN_7ffa1b2ec8c0(*param_2 + uVar4 * 8,0,
                               (*(ushort *)((longlong)param_2 + 10) - uVar4) * 8);
            }
            FUN_7ffa1b2ecc80(*param_2,local_158,uVar4 * 8);
          }
        }
        if (ppuVar1 != &local_148) {
          uVar3 = (ulonglong)local_140._2_2_;
          if (local_140._2_2_ == 0) {
            if (*(ushort *)((longlong)param_2 + 0x1a) != 0) {
              *(undefined2 *)(param_2 + 3) = 1;
              FUN_7ffa1b2ec8c0(*ppuVar1,0,(ulonglong)*(ushort *)((longlong)param_2 + 0x1a) << 3);
            }
          }
          else {
            do {
              uVar4 = uVar3;
              uVar3 = uVar4 - 1;
              if (uVar3 == 0) break;
            } while (*(longlong *)(local_148 + uVar3 * 8) == 0);
            *(undefined2 *)(param_2 + 3) = (undefined2)local_140;
            if (*(ushort *)((longlong)param_2 + 0x1a) < uVar4) {
              iVar5 = FUN_7ffa1b045900(ppuVar1,uVar4);
              if (iVar5 != 0) goto LAB_7ffa1b03db6f;
            }
            else {
              FUN_7ffa1b2ec8c0(*ppuVar1 + uVar4 * 8,0,
                               (*(ushort *)((longlong)param_2 + 0x1a) - uVar4) * 8);
            }
            FUN_7ffa1b2ecc80(*ppuVar1,local_148,uVar4 * 8);
          }
        }
        iVar5 = 0;
        if (ppuVar2 != &local_138) {
          uVar3 = (ulonglong)local_130._2_2_;
          if (local_130._2_2_ == 0) {
            if (*(ushort *)((longlong)param_2 + 0x2a) != 0) {
              *(undefined2 *)(param_2 + 5) = 1;
              FUN_7ffa1b2ec8c0(*ppuVar2,0,(ulonglong)*(ushort *)((longlong)param_2 + 0x2a) << 3);
            }
          }
          else {
            do {
              uVar4 = uVar3;
              uVar3 = uVar4 - 1;
              if (uVar3 == 0) break;
            } while (*(longlong *)(puVar10 + uVar3 * 8) == 0);
            *(undefined2 *)(param_2 + 5) = (undefined2)local_130;
            if (*(ushort *)((longlong)param_2 + 0x2a) < uVar4) {
              iVar5 = FUN_7ffa1b045900(ppuVar2,uVar4);
              if (iVar5 == 0) {
                FUN_7ffa1b2ecc80(*ppuVar2,puVar10,uVar4 * 8);
              }
            }
            else {
              FUN_7ffa1b2ec8c0(*ppuVar2 + uVar4 * 8,0,
                               (*(ushort *)((longlong)param_2 + 0x2a) - uVar4) * 8);
              FUN_7ffa1b2ecc80(*ppuVar2,puVar10,uVar4 * 8);
            }
          }
        }
      }
      else {
        local_110 = &local_168;
        local_168 = 0;
        local_108 = 0x10001;
        iVar5 = FUN_7ffa1b046600(&local_138,&local_110);
        if (iVar5 == 0) {
          iVar5 = FUN_7ffa1b039390(param_2,param_2);
        }
        else {
          local_100 = &local_168;
          local_168 = 1;
          local_f8 = 0x10001;
          iVar5 = FUN_7ffa1b046600(&local_138,&local_100);
          if (iVar5 != 0) goto LAB_7ffa1b03db85;
          iVar5 = FUN_7ffa1b0398e0(param_1,&local_88,ppuVar2,ppuVar2);
          if (((iVar5 == 0) &&
              (iVar5 = FUN_7ffa1b0398e0(param_1,&local_78,&local_88,ppuVar2), iVar5 == 0)) &&
             ((iVar5 = FUN_7ffa1b0398e0(param_1,&local_88,&local_88,&local_158), iVar5 == 0 &&
              (iVar5 = FUN_7ffa1b0398e0(param_1,&local_78,&local_78,&local_148), iVar5 == 0)))) {
            iVar5 = FUN_7ffa1b0469c0(&local_88,&local_88,param_2,0xffffffff);
            if ((iVar5 == 0) && ((short)local_80 < 0)) {
              local_168 = 0;
              do {
                local_f0 = &local_168;
                local_e8 = 0x10001;
                iVar6 = FUN_7ffa1b046600(&local_88,&local_f0);
                if (iVar6 == 0) break;
                iVar5 = FUN_7ffa1b0469c0(&local_88,&local_88,param_1 + 8,1);
                if (iVar5 != 0) goto LAB_7ffa1b03db6f;
                iVar5 = 0;
              } while ((short)local_80 < 0);
            }
            if ((iVar5 == 0) &&
               (iVar5 = FUN_7ffa1b039a60(param_1,&local_78,&local_78,ppuVar1), iVar5 == 0)) {
              local_e0 = &local_168;
              local_d8 = 0x10001;
              local_168 = 0;
              iVar5 = FUN_7ffa1b046600(&local_88,&local_e0);
              if (iVar5 == 0) {
                local_d0 = &local_168;
                local_168 = 0;
                local_c8 = 0x10001;
                iVar5 = FUN_7ffa1b046600(&local_78,&local_d0);
                if (iVar5 == 0) {
                  iVar5 = FUN_7ffa1b03bd10(param_1,param_2,param_2,&local_88);
                }
                else {
                  iVar5 = FUN_7ffa1b039490(param_2);
                }
              }
              else {
                iVar5 = FUN_7ffa1b0398e0(param_1,ppuVar2,ppuVar2,&local_88);
                if (((((iVar5 == 0) &&
                      (iVar5 = FUN_7ffa1b0398e0(param_1,&local_68,&local_88,&local_88), iVar5 == 0))
                     && (iVar5 = FUN_7ffa1b0398e0(param_1,&local_58,&local_68,&local_88), iVar5 == 0
                        )) && ((iVar5 = FUN_7ffa1b0398e0(param_1,&local_68,&local_68,param_2),
                               iVar5 == 0 &&
                               (iVar5 = FUN_7ffa1b045c10(&local_88,&local_68), iVar5 == 0)))) &&
                   ((iVar5 = FUN_7ffa1b039c20(param_1,&local_88), iVar5 == 0 &&
                    (iVar5 = FUN_7ffa1b0398e0(param_1,param_2,&local_78,&local_78), iVar5 == 0)))) {
                  iVar5 = FUN_7ffa1b0469c0(param_2,param_2,&local_88,0xffffffff);
                  if ((iVar5 == 0) && (*(short *)(param_2 + 1) < 0)) {
                    local_168 = 0;
                    do {
                      local_c0 = &local_168;
                      local_b8 = 0x10001;
                      iVar6 = FUN_7ffa1b046600(param_2,&local_c0);
                      if (iVar6 == 0) break;
                      iVar5 = FUN_7ffa1b0469c0(param_2,param_2,param_1 + 8,1);
                      if (iVar5 != 0) goto LAB_7ffa1b03db6f;
                      iVar5 = 0;
                    } while (*(short *)(param_2 + 1) < 0);
                  }
                  if (iVar5 == 0) {
                    iVar5 = FUN_7ffa1b0469c0(param_2,param_2,&local_58,0xffffffff);
                    if ((iVar5 == 0) && (*(short *)(param_2 + 1) < 0)) {
                      local_168 = 0;
                      do {
                        local_b0 = &local_168;
                        local_a8 = 0x10001;
                        iVar6 = FUN_7ffa1b046600(param_2,&local_b0);
                        if (iVar6 == 0) break;
                        iVar5 = FUN_7ffa1b0469c0(param_2,param_2,param_1 + 8,1);
                        if (iVar5 != 0) goto LAB_7ffa1b03db6f;
                        iVar5 = 0;
                      } while (*(short *)(param_2 + 1) < 0);
                    }
                    if ((((iVar5 == 0) &&
                         (iVar5 = FUN_7ffa1b039a60(param_1,&local_68,&local_68,param_2), iVar5 == 0)
                         ) && (iVar5 = FUN_7ffa1b0398e0(param_1,&local_68,&local_68,&local_78),
                              iVar5 == 0)) &&
                       (((iVar5 = FUN_7ffa1b0398e0(param_1,&local_58,&local_58,ppuVar1), iVar5 == 0
                         && (iVar5 = FUN_7ffa1b0469c0(ppuVar1,&local_68,&local_58,0xffffffff),
                            iVar5 == 0)) && (*(short *)(param_2 + 3) < 0)))) {
                      local_168 = 0;
                      do {
                        local_a0 = &local_168;
                        local_98 = 0x10001;
                        iVar6 = FUN_7ffa1b046600(ppuVar1,&local_a0);
                        if ((iVar6 == 0) ||
                           (iVar5 = FUN_7ffa1b0469c0(ppuVar1,ppuVar1,param_1 + 8,1), iVar5 != 0))
                        break;
                      } while (*(short *)(param_2 + 3) < 0);
                    }
                  }
                }
              }
            }
          }
        }
      }
LAB_7ffa1b03db6f:
      if ((iVar5 != 0) || (param_6 == 0)) break;
    }
    puVar9 = local_148;
  }
  if (local_158 != (undefined1 *)0x0) {
    lVar7 = (ulonglong)local_150._2_2_ << 3;
    if ((ulonglong)local_150._2_2_ != 0) {
      puVar8 = local_158;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *puVar8 = 0;
        puVar8 = puVar8 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_158);
  }
  if (puVar9 != (undefined1 *)0x0) {
    lVar7 = (ulonglong)local_140._2_2_ << 3;
    if ((ulonglong)local_140._2_2_ != 0) {
      puVar8 = puVar9;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *puVar8 = 0;
        puVar8 = puVar8 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar9);
  }
  if (puVar10 != (undefined1 *)0x0) {
    lVar7 = (ulonglong)local_130._2_2_ << 3;
    if ((ulonglong)local_130._2_2_ != 0) {
      puVar9 = puVar10;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *puVar9 = 0;
        puVar9 = puVar9 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar10);
  }
  if (local_88 != (undefined1 *)0x0) {
    lVar7 = (ulonglong)local_80._2_2_ << 3;
    if ((ulonglong)local_80._2_2_ != 0) {
      puVar10 = local_88;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *puVar10 = 0;
        puVar10 = puVar10 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_88);
  }
  local_80 = 1;
  local_88 = (undefined1 *)0x0;
  if (local_78 != (undefined1 *)0x0) {
    lVar7 = (ulonglong)local_70._2_2_ << 3;
    if ((ulonglong)local_70._2_2_ != 0) {
      puVar10 = local_78;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *puVar10 = 0;
        puVar10 = puVar10 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_78);
  }
  local_70 = 1;
  local_78 = (undefined1 *)0x0;
  if (local_68 != (undefined1 *)0x0) {
    lVar7 = (ulonglong)local_60._2_2_ << 3;
    if ((ulonglong)local_60._2_2_ != 0) {
      puVar10 = local_68;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *puVar10 = 0;
        puVar10 = puVar10 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_68);
  }
  local_60 = 1;
  local_68 = (undefined1 *)0x0;
  if (local_58 != (undefined1 *)0x0) {
    lVar7 = (ulonglong)local_50._2_2_ << 3;
    if ((ulonglong)local_50._2_2_ != 0) {
      puVar10 = local_58;
      for (; lVar7 != 0; lVar7 = lVar7 + -1) {
        *puVar10 = 0;
        puVar10 = puVar10 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_58);
  }
  return iVar5;
}



// ==================================================================

/* ===== 0x03bbc0  73 行 ===== */
// FUN_7ffa1b03bbc0 @ 0x7ffa1b03bbc0
// signature: undefined FUN_7ffa1b03bbc0()
// ==================================================================

int FUN_7ffa1b03bbc0(longlong param_1,longlong param_2,byte param_3)

{
  int iVar1;
  int iVar2;
  int iVar3;
  longlong lVar4;
  short sVar5;
  undefined1 *puVar6;
  undefined8 local_res8;
  undefined1 *local_48;
  undefined4 local_40;
  undefined8 *local_38;
  undefined4 local_30;
  
  lVar4 = param_2 + 0x10;
  local_48 = (undefined1 *)0x0;
  local_res8 = 0;
  local_38 = &local_res8;
  local_30 = 0x10001;
  local_40 = 1;
  iVar1 = FUN_7ffa1b046600(lVar4,&local_38);
  sVar5 = *(short *)(param_1 + 0x10);
  param_1 = param_1 + 8;
  if (-((int)*(short *)(param_2 + 0x18) * (int)sVar5) < 0) {
    iVar2 = FUN_7ffa1b046560(param_1,lVar4);
    if (iVar2 < 0) {
      iVar3 = FUN_7ffa1b046830(&local_48,lVar4,param_1);
      if (iVar3 != 0) goto LAB_7ffa1b03bca0;
      local_40 = CONCAT22(local_40._2_2_,-sVar5);
    }
    else {
      iVar3 = FUN_7ffa1b046830(&local_48,param_1,lVar4);
      if (iVar3 == 0) {
        if (iVar2 == 0) {
          sVar5 = 1;
        }
        local_40 = CONCAT22(local_40._2_2_,sVar5);
      }
      else {
LAB_7ffa1b03bca0:
        if (iVar3 != 0) goto LAB_7ffa1b03bcba;
      }
    }
  }
  else {
    iVar3 = FUN_7ffa1b0466e0(&local_48,param_1,lVar4);
    if (iVar3 != 0) goto LAB_7ffa1b03bca0;
    local_40 = CONCAT22(local_40._2_2_,sVar5);
  }
  iVar3 = FUN_7ffa1b0456a0(lVar4,&local_48,iVar1 != 0 & param_3);
LAB_7ffa1b03bcba:
  if (local_48 != (undefined1 *)0x0) {
    lVar4 = (ulonglong)local_40._2_2_ << 3;
    if ((ulonglong)local_40._2_2_ != 0) {
      puVar6 = local_48;
      for (; lVar4 != 0; lVar4 = lVar4 + -1) {
        *puVar6 = 0;
        puVar6 = puVar6 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_48);
  }
  return iVar3;
}



// ==================================================================

/* ===== 0x03a610  333 行 ===== */
// FUN_7ffa1b03a610 @ 0x7ffa1b03a610
// signature: undefined FUN_7ffa1b03a610()
// ==================================================================

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

ulonglong FUN_7ffa1b03a610(longlong param_1,longlong param_2)

{
  code *pcVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  ulonglong uVar5;
  longlong *plVar6;
  ulonglong *puVar7;
  ulonglong uVar8;
  ulonglong uVar9;
  longlong lVar10;
  ulonglong uVar11;
  short sVar12;
  undefined1 *puVar13;
  undefined1 *puVar14;
  bool bVar15;
  longlong local_res18 [2];
  ulonglong auStack_70 [2];
  undefined1 *local_60;
  undefined4 local_58;
  longlong *local_50;
  undefined4 local_48;
  
  local_48 = 0x10001;
  local_50 = local_res18;
  local_res18[0] = 0;
  uVar5 = FUN_7ffa1b046600(param_2 + 0x20,&local_50);
  if ((int)uVar5 == 0) {
    return uVar5;
  }
  local_58 = 1;
  local_60 = (undefined1 *)0x0;
  uVar2 = FUN_7ffa1b048ce0(0,&local_60,param_2 + 0x20,param_1 + 8);
  uVar5 = (ulonglong)uVar2;
  if (uVar2 == 0) {
    lVar10 = param_2 + 0x10;
    uVar2 = FUN_7ffa1b046d10(lVar10,lVar10,&local_60);
    uVar5 = (ulonglong)uVar2;
    if (uVar2 == 0) {
      pcVar1 = *(code **)(param_1 + 0x90);
      if (pcVar1 == (code *)0x0) {
        uVar5 = FUN_7ffa1b048740(lVar10,lVar10,param_1 + 8);
        uVar5 = uVar5 & 0xffffffff;
LAB_7ffa1b03a7b5:
        if ((int)uVar5 == 0) {
          _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
          uVar2 = FUN_7ffa1b046d10(&local_60,&local_60,&local_60);
          uVar5 = (ulonglong)uVar2;
          if (uVar2 == 0) {
            if (*(code **)(param_1 + 0x90) != (code *)0x0) {
              if ((short)local_58 < 0) {
                uVar5 = (ulonglong)local_58._2_2_;
                local_res18[0] = 0;
                if (uVar5 != 0) {
                  plVar6 = (longlong *)(local_60 + (uVar5 - 1) * 8);
                  do {
                    if (*plVar6 != 0) break;
                    plVar6 = plVar6 + -1;
                    uVar5 = uVar5 - 1;
                  } while (uVar5 != 0);
                }
                uVar8 = 1;
                plVar6 = local_res18;
                do {
                  if (*plVar6 != 0) break;
                  plVar6 = plVar6 + -1;
                  uVar8 = uVar8 - 1;
                } while (uVar8 != 0);
                if (uVar5 == 0) {
                  bVar15 = uVar8 == 0;
LAB_7ffa1b03a872:
                  if (bVar15) goto LAB_7ffa1b03a874;
                }
                else if (uVar8 < uVar5) {
                  bVar15 = (short)local_58 == 0;
                  goto LAB_7ffa1b03a872;
                }
              }
              else {
LAB_7ffa1b03a874:
                uVar5 = (ulonglong)local_58._2_2_;
                uVar2 = (uint)local_58._2_2_;
                do {
                  uVar5 = uVar5 - 1;
                  if ((longlong)uVar5 < 0) {
                    uVar5 = 0;
                    goto LAB_7ffa1b03a892;
                  }
                  uVar2 = uVar2 - 1;
                } while (*(longlong *)(local_60 + uVar5 * 8) == 0);
                uVar8 = 0x8000000000000000;
                uVar5 = 0;
                do {
                  if ((uVar8 & *(ulonglong *)(local_60 + (longlong)(int)uVar2 * 8)) != 0) break;
                  uVar8 = uVar8 >> 1;
                  uVar5 = uVar5 + 1;
                } while (uVar5 < 0x40);
                uVar5 = ((longlong)(int)uVar2 + 1) * 0x40 - uVar5;
LAB_7ffa1b03a892:
                if (uVar5 <= (ulonglong)(*(longlong *)(param_1 + 0x78) * 2)) {
                  uVar2 = (**(code **)(param_1 + 0x90))(&local_60);
                  uVar5 = (ulonglong)uVar2;
                  if (uVar2 == 0) {
                    uVar2 = local_58 & 0xffff;
                    if ((short)local_58 < 0) {
                      auStack_70[1] = 0;
                      do {
                        uVar11 = (ulonglong)local_58._2_2_;
                        uVar8 = uVar11;
                        if (uVar11 != 0) {
                          plVar6 = (longlong *)(local_60 + uVar11 * 8 + -8);
                          do {
                            if (*plVar6 != 0) break;
                            plVar6 = plVar6 + -1;
                            uVar8 = uVar8 - 1;
                          } while (uVar8 != 0);
                        }
                        puVar7 = auStack_70 + 1;
                        uVar9 = 1;
                        do {
                          if (*puVar7 != 0) break;
                          puVar7 = puVar7 + -1;
                          uVar9 = uVar9 - 1;
                        } while (uVar9 != 0);
                        sVar12 = (short)uVar2;
                        if (uVar8 == 0) {
                          if (uVar9 == 0) break;
LAB_7ffa1b03a964:
                          if ((uVar9 <= uVar8) && (-1 < sVar12)) {
                            if (uVar8 != 0) {
                              puVar7 = auStack_70 + uVar8;
                              while (uVar9 = *(ulonglong *)
                                              (((longlong)local_60 - (longlong)(auStack_70 + 1)) +
                                              (longlong)puVar7), uVar9 <= *puVar7) {
                                if (uVar9 < *puVar7) {
                                  iVar4 = -(int)sVar12;
                                  goto LAB_7ffa1b03a9ba;
                                }
                                puVar7 = puVar7 + -1;
                                uVar8 = uVar8 - 1;
                                if (uVar8 == 0) goto LAB_7ffa1b03aada;
                              }
                              goto LAB_7ffa1b03a9b7;
                            }
                            break;
                          }
                        }
                        else {
                          if (uVar8 <= uVar9) goto LAB_7ffa1b03a964;
LAB_7ffa1b03a9b7:
                          iVar4 = (int)sVar12;
LAB_7ffa1b03a9ba:
                          if (iVar4 == 0) break;
                        }
                        uVar2 = (uint)sVar12;
                        if ((int)((int)*(short *)(param_1 + 0x10) * uVar2) < 0) {
                          if (uVar11 != 0) {
                            plVar6 = (longlong *)(local_60 + (uVar11 - 1) * 8);
                            do {
                              if (*plVar6 != 0) break;
                              plVar6 = plVar6 + -1;
                              uVar11 = uVar11 - 1;
                            } while (uVar11 != 0);
                          }
                          uVar5 = (ulonglong)*(ushort *)(param_1 + 0x12);
                          if (uVar5 != 0) {
                            plVar6 = (longlong *)(*(longlong *)(param_1 + 8) + uVar5 * 8);
                            do {
                              plVar6 = plVar6 + -1;
                              if (*plVar6 != 0) break;
                              uVar5 = uVar5 - 1;
                            } while (uVar5 != 0);
                          }
                          if (uVar5 < uVar11) {
LAB_7ffa1b03aa25:
                            bVar15 = true;
                          }
                          else {
                            if (uVar11 < uVar5) {
LAB_7ffa1b03aa80:
                              uVar3 = FUN_7ffa1b046830(&local_60,param_1 + 8,&local_60);
                              if (uVar3 != 0) goto LAB_7ffa1b03aabd;
                              uVar2 = (uint)(ushort)-sVar12;
                              uVar5 = 0;
                              local_58 = CONCAT22(local_58._2_2_,-sVar12);
                              goto LAB_7ffa1b03aac7;
                            }
                            if (uVar11 != 0) {
                              puVar7 = (ulonglong *)(local_60 + uVar11 * 8 + -8);
                              do {
                                uVar5 = *(ulonglong *)
                                         ((*(longlong *)(param_1 + 8) - (longlong)local_60) +
                                         (longlong)puVar7);
                                if (uVar5 < *puVar7) goto LAB_7ffa1b03aa25;
                                if (*puVar7 < uVar5) goto LAB_7ffa1b03aa80;
                                puVar7 = puVar7 + -1;
                                uVar11 = uVar11 - 1;
                              } while (uVar11 != 0);
                            }
                            bVar15 = false;
                          }
                          uVar3 = FUN_7ffa1b046830(&local_60,&local_60,param_1 + 8);
                          if (uVar3 != 0) goto LAB_7ffa1b03aabd;
                          uVar5 = 0;
                          if (!bVar15) {
                            uVar2 = 1;
                          }
                          local_58 = CONCAT22(local_58._2_2_,(short)uVar2);
                        }
                        else {
                          uVar3 = FUN_7ffa1b0466e0(&local_60,&local_60,param_1 + 8);
                          if (uVar3 == 0) {
                            local_58 = CONCAT22(local_58._2_2_,sVar12);
                            uVar5 = 0;
                          }
                          else {
LAB_7ffa1b03aabd:
                            uVar5 = (ulonglong)uVar3;
                            if (uVar3 != 0) goto LAB_7ffa1b03ab18;
                            uVar2 = local_58 & 0xffff;
                          }
                        }
LAB_7ffa1b03aac7:
                      } while ((short)uVar2 < 0);
                    }
LAB_7ffa1b03aada:
                    puVar14 = local_60;
                    iVar4 = FUN_7ffa1b046600(&local_60,param_1 + 8);
                    if (iVar4 < 0) goto LAB_7ffa1b03ab20;
                    do {
                      uVar2 = FUN_7ffa1b046830(&local_60,&local_60,param_1 + 8);
                      uVar5 = (ulonglong)uVar2;
                      if (uVar2 != 0) break;
                      iVar4 = FUN_7ffa1b046600(&local_60,param_1 + 8);
                    } while (-1 < iVar4);
                  }
LAB_7ffa1b03ab18:
                  puVar14 = local_60;
                  goto LAB_7ffa1b03ab20;
                }
              }
              uVar5 = 0xffffb080;
              puVar14 = local_60;
              goto LAB_7ffa1b03ab6e;
            }
            uVar5 = FUN_7ffa1b048740(&local_60,&local_60,param_1 + 8);
            uVar5 = uVar5 & 0xffffffff;
            puVar14 = local_60;
LAB_7ffa1b03ab20:
            if ((int)uVar5 != 0) goto LAB_7ffa1b03ab6e;
            _DAT_7ffa1b3a1948 = _DAT_7ffa1b3a1948 + 1;
            uVar2 = FUN_7ffa1b0398e0(param_1,param_2,param_2,&local_60);
            uVar5 = (ulonglong)uVar2;
            if (uVar2 == 0) {
              uVar2 = FUN_7ffa1b0398e0(param_1,lVar10,lVar10,&local_60);
              uVar5 = (ulonglong)uVar2;
              if (uVar2 == 0) {
                uVar5 = FUN_7ffa1b045d10(param_2 + 0x20,1);
                uVar5 = uVar5 & 0xffffffff;
              }
            }
          }
        }
      }
      else {
        if (*(short *)(param_2 + 0x18) < 0) {
          local_50 = local_res18;
          local_res18[0] = 0;
          local_48 = 0x10001;
          iVar4 = FUN_7ffa1b046600(lVar10,&local_50);
          if (iVar4 == 0) goto LAB_7ffa1b03a704;
        }
        else {
LAB_7ffa1b03a704:
          uVar5 = FUN_7ffa1b045fd0(lVar10);
          if (uVar5 <= (ulonglong)(*(longlong *)(param_1 + 0x78) * 2)) {
            uVar2 = (*pcVar1)(lVar10);
            uVar5 = (ulonglong)uVar2;
            if (uVar2 == 0) {
              if (*(short *)(param_2 + 0x18) < 0) {
                local_res18[0] = 0;
                do {
                  local_50 = local_res18;
                  local_48 = 0x10001;
                  iVar4 = FUN_7ffa1b046600(lVar10,&local_50);
                  if (iVar4 == 0) break;
                  uVar2 = FUN_7ffa1b0469c0(lVar10,lVar10,param_1 + 8,1);
                  uVar5 = (ulonglong)uVar2;
                  if (uVar2 != 0) goto LAB_7ffa1b03a7b5;
                } while (*(short *)(param_2 + 0x18) < 0);
              }
              iVar4 = FUN_7ffa1b046600(lVar10,param_1 + 8);
              while (-1 < iVar4) {
                uVar2 = FUN_7ffa1b046830(lVar10,lVar10,param_1 + 8);
                uVar5 = (ulonglong)uVar2;
                if (uVar2 != 0) break;
                iVar4 = FUN_7ffa1b046600(lVar10,param_1 + 8);
              }
            }
            goto LAB_7ffa1b03a7b5;
          }
        }
        uVar5 = 0xffffb080;
      }
    }
  }
  puVar14 = local_60;
LAB_7ffa1b03ab6e:
  if (puVar14 != (undefined1 *)0x0) {
    lVar10 = (ulonglong)local_58._2_2_ << 3;
    if ((ulonglong)local_58._2_2_ != 0) {
      puVar13 = puVar14;
      for (; lVar10 != 0; lVar10 = lVar10 + -1) {
        *puVar13 = 0;
        puVar13 = puVar13 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(puVar14);
  }
  return uVar5;
}



// ==================================================================

/* ===== 0x03ceb0  198 行 ===== */
// FUN_7ffa1b03ceb0 @ 0x7ffa1b03ceb0
// signature: undefined FUN_7ffa1b03ceb0()
// ==================================================================

/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */

int FUN_7ffa1b03ceb0(undefined8 param_1,longlong param_2,undefined8 param_3,byte param_4,
                    ulonglong param_5)

{
  byte bVar1;
  int iVar2;
  ulonglong uVar3;
  undefined8 *puVar4;
  longlong lVar5;
  undefined1 *puVar6;
  undefined1 *puVar7;
  byte bVar8;
  uint uVar9;
  longlong lVar10;
  ulonglong uVar11;
  undefined1 auStack_f8 [32];
  undefined1 **local_d8;
  uint local_c8;
  undefined8 local_c0;
  undefined1 *local_b8;
  undefined4 local_b0;
  undefined1 *local_a8;
  undefined4 local_a0;
  undefined1 *local_98;
  undefined4 local_90;
  undefined1 *local_88;
  undefined4 local_80;
  longlong local_78 [8];
  
  local_78[7] = DAT_7ffa1b381040 ^ (ulonglong)auStack_f8;
  uVar3 = 0;
  local_78[0] = 0;
  local_b0 = 1;
  local_b8 = (undefined1 *)0x0;
  local_a0 = 1;
  bVar8 = '\x01' << (param_4 - 1 & 0x1f);
  uVar9 = (uint)bVar8;
  local_c8 = (uint)bVar8;
  local_78[1] = 0;
  local_78[2] = 0;
  local_a8 = (undefined1 *)0x0;
  local_78[3] = 0;
  local_78[4] = 0;
  local_90 = 1;
  local_78[5] = 0;
  local_78[6] = 0;
  local_98 = (undefined1 *)0x0;
  local_80 = 1;
  local_88 = (undefined1 *)0x0;
  local_c0 = param_1;
  iVar2 = FUN_7ffa1b039390(param_2);
  if (iVar2 == 0) {
    uVar11 = ((ulonglong)param_4 - 1) * param_5;
    if (uVar11 != 0) {
      do {
        bVar1 = '\x01' << ((byte)(uVar3 / param_5) & 0x1f);
        lVar5 = (ulonglong)bVar1 * 0x30 + param_2;
        if (((uVar3 % param_5 == 0) &&
            (iVar2 = FUN_7ffa1b039390(lVar5,(ulonglong)(bVar1 >> 1) * 0x30 + param_2), iVar2 != 0))
           || (iVar2 = FUN_7ffa1b03bd10(param_1,lVar5,lVar5,&local_b8), iVar2 != 0))
        goto LAB_7ffa1b03d121;
        uVar3 = uVar3 + 1;
      } while (uVar3 < uVar11);
    }
    lVar5 = 0;
    uVar3 = 1;
    if (1 < bVar8) {
      do {
        bVar1 = (char)uVar3 * '\x02';
        local_78[lVar5] = uVar3 * 0x30 + param_2;
        lVar5 = lVar5 + 1;
        uVar3 = (ulonglong)bVar1;
      } while (bVar1 < bVar8);
    }
    iVar2 = FUN_7ffa1b03abb0(param_1,local_78);
    if (iVar2 == 0) {
      bVar1 = 1;
      if (1 < bVar8) {
        do {
          uVar3 = (ulonglong)bVar1;
          if (bVar1 != 0) {
            lVar10 = uVar3 * 0x30 + param_2;
            lVar5 = lVar10;
            uVar11 = uVar3;
            do {
              uVar11 = uVar11 - 1;
              lVar5 = lVar5 + -0x30;
              local_d8 = &local_b8;
              iVar2 = FUN_7ffa1b03c3e0(local_c0,(uVar3 + uVar11) * 0x30 + param_2,lVar5,lVar10);
              if (iVar2 != 0) goto LAB_7ffa1b03d121;
            } while (uVar11 != 0);
            uVar9 = local_c8;
          }
          bVar1 = bVar1 * '\x02';
        } while (bVar1 < (byte)uVar9);
        param_1 = local_c0;
      }
      uVar3 = (ulonglong)(uVar9 & 0xff);
      lVar5 = 0;
      if (1 < uVar3) {
        uVar11 = 1;
        lVar10 = param_2;
        do {
          lVar10 = lVar10 + 0x30;
          local_78[lVar5] = lVar10;
          uVar11 = uVar11 + 1;
          lVar5 = lVar5 + 1;
        } while (uVar11 < uVar3);
      }
      iVar2 = FUN_7ffa1b03abb0(param_1,local_78);
      if ((iVar2 == 0) && ((char)local_c8 != '\0')) {
        puVar4 = (undefined8 *)(param_2 + 0x20);
        do {
          if (puVar4 != (undefined8 *)0x0) {
            puVar7 = (undefined1 *)*puVar4;
            if (puVar7 != (undefined1 *)0x0) {
              lVar5 = (ulonglong)*(ushort *)((longlong)puVar4 + 10) << 3;
              if ((ulonglong)*(ushort *)((longlong)puVar4 + 10) != 0) {
                puVar6 = puVar7;
                for (; lVar5 != 0; lVar5 = lVar5 + -1) {
                  *puVar6 = 0;
                  puVar6 = puVar6 + 1;
                }
              }
              thunk_FUN_7ffa1b0c8950(puVar7);
            }
            *(undefined4 *)(puVar4 + 1) = 1;
            *puVar4 = 0;
          }
          puVar4 = puVar4 + 6;
          uVar3 = uVar3 - 1;
        } while (uVar3 != 0);
      }
    }
  }
LAB_7ffa1b03d121:
  if (local_b8 != (undefined1 *)0x0) {
    lVar5 = (ulonglong)local_b0._2_2_ << 3;
    if ((ulonglong)local_b0._2_2_ != 0) {
      puVar7 = local_b8;
      for (; lVar5 != 0; lVar5 = lVar5 + -1) {
        *puVar7 = 0;
        puVar7 = puVar7 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_b8);
  }
  local_b0 = 1;
  local_b8 = (undefined1 *)0x0;
  if (local_a8 != (undefined1 *)0x0) {
    lVar5 = (ulonglong)local_a0._2_2_ << 3;
    if ((ulonglong)local_a0._2_2_ != 0) {
      puVar7 = local_a8;
      for (; lVar5 != 0; lVar5 = lVar5 + -1) {
        *puVar7 = 0;
        puVar7 = puVar7 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_a8);
  }
  local_a0 = 1;
  local_a8 = (undefined1 *)0x0;
  if (local_98 != (undefined1 *)0x0) {
    lVar5 = (ulonglong)local_90._2_2_ << 3;
    if ((ulonglong)local_90._2_2_ != 0) {
      puVar7 = local_98;
      for (; lVar5 != 0; lVar5 = lVar5 + -1) {
        *puVar7 = 0;
        puVar7 = puVar7 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_98);
  }
  local_90 = 1;
  local_98 = (undefined1 *)0x0;
  if (local_88 != (undefined1 *)0x0) {
    lVar5 = (ulonglong)local_80._2_2_ << 3;
    if ((ulonglong)local_80._2_2_ != 0) {
      puVar7 = local_88;
      for (; lVar5 != 0; lVar5 = lVar5 + -1) {
        *puVar7 = 0;
        puVar7 = puVar7 + 1;
      }
    }
    thunk_FUN_7ffa1b0c8950(local_88);
  }
  return iVar2;
}



// ==================================================================

/* ===== 0x03d200  41 行 ===== */
// FUN_7ffa1b03d200 @ 0x7ffa1b03d200
// signature: undefined FUN_7ffa1b03d200()
// ==================================================================

void FUN_7ffa1b03d200(undefined8 param_1,longlong param_2,longlong param_3,byte param_4,byte param_5
                     )

{
  int iVar1;
  byte bVar2;
  ulonglong uVar3;
  longlong lVar4;
  bool bVar5;
  
  uVar3 = 0;
  if (param_4 != 0) {
    do {
      bVar2 = (byte)uVar3;
      bVar5 = bVar2 == (param_5 >> 1 & 0x3f);
      lVar4 = uVar3 * 0x30 + param_3;
      iVar1 = FUN_7ffa1b0456a0(param_2,lVar4,bVar5);
      if (iVar1 != 0) {
        return;
      }
      iVar1 = FUN_7ffa1b0456a0(param_2 + 0x10,lVar4 + 0x10,bVar5);
      if (iVar1 != 0) {
        return;
      }
      uVar3 = (ulonglong)(byte)(bVar2 + 1);
    } while ((byte)(bVar2 + 1) < param_4);
  }
  iVar1 = FUN_7ffa1b03bbc0(param_1,param_2,param_5 >> 7);
  if (iVar1 == 0) {
    FUN_7ffa1b045d10(param_2 + 0x20,1);
  }
  return;
}



// ==================================================================

/* ===== 0x03e180  131 行 ===== */
// FUN_7ffa1b03e180 @ 0x7ffa1b03e180
// signature: undefined FUN_7ffa1b03e180()
// ==================================================================

/* WARNING: Function: __security_check_cookie replaced with injection: security_check_cookie */

int FUN_7ffa1b03e180(longlong param_1,undefined8 param_2,undefined8 param_3,longlong param_4,
                    undefined8 param_5,undefined8 param_6)

{
  bool bVar1;
  undefined1 *puVar2;
  bool bVar3;
  int iVar4;
  longlong lVar5;
  longlong lVar6;
  byte bVar7;
  longlong lVar8;
  ulonglong uVar9;
  byte bVar10;
  undefined1 auStack_1e8 [32];
  undefined1 *local_1c8;
  undefined1 *local_1c0;
  undefined8 local_1b8;
  undefined8 local_1b0;
  undefined1 local_198 [8];
  undefined1 *local_190;
  longlong local_188;
  undefined8 local_180;
  undefined8 local_178;
  undefined8 local_170;
  undefined1 local_168 [272];
  ulonglong local_58;
  
  local_58 = DAT_7ffa1b381040 ^ (ulonglong)auStack_1e8;
  local_170 = param_5;
  local_178 = param_6;
  local_188 = param_4;
  local_180 = param_3;
  iVar4 = FUN_7ffa1b046600(param_4 + 0x10,param_1 + 0x48);
  if ((iVar4 == 0) && (iVar4 = FUN_7ffa1b046600(param_4,param_1 + 0x38), iVar4 == 0)) {
    uVar9 = *(ulonglong *)(param_1 + 0x80);
    bVar1 = true;
    bVar7 = (0x17f < uVar9) + 5;
    bVar3 = true;
    if ((*(longlong *)(param_1 + 0xb0) == 0) || (*(longlong *)(param_1 + 0xb8) != 0))
    goto LAB_7ffa1b03e23a;
  }
  else {
    uVar9 = *(ulonglong *)(param_1 + 0x80);
    bVar7 = (0x17f < uVar9) + 4;
    bVar3 = false;
LAB_7ffa1b03e23a:
    bVar1 = bVar3;
    if (4 < bVar7) {
      bVar7 = 4;
    }
  }
  if (uVar9 <= bVar7) {
    bVar7 = 2;
  }
  lVar8 = 0;
  bVar10 = '\x01' << (bVar7 - 1 & 0x1f);
  local_190 = (undefined1 *)(((uVar9 - 1) + (ulonglong)bVar7) / (ulonglong)bVar7);
  if ((!bVar1) || (lVar5 = *(longlong *)(param_1 + 0xb0), lVar5 == 0)) {
    uVar9 = (ulonglong)bVar10;
    lVar5 = _calloc_base(uVar9,0x30);
    if (lVar5 == 0) {
      iVar4 = -0x4d80;
      goto LAB_7ffa1b03e3ce;
    }
    if (bVar10 != 0) {
      lVar6 = lVar5 + 10;
      do {
        *(undefined4 *)(lVar6 + -2) = 1;
        *(undefined8 *)(lVar6 + -10) = 0;
        *(undefined4 *)(lVar6 + 0xe) = 1;
        *(undefined8 *)(lVar6 + 6) = 0;
        *(undefined4 *)(lVar6 + 0x1e) = 1;
        *(undefined8 *)(lVar6 + 0x16) = 0;
        lVar6 = lVar6 + 0x30;
        uVar9 = uVar9 - 1;
      } while (uVar9 != 0);
    }
    local_1c8 = local_190;
    iVar4 = FUN_7ffa1b03ceb0(param_1,lVar5,local_188,bVar7);
    if (iVar4 != 0) goto LAB_7ffa1b03e3ce;
    if (bVar1) {
      *(ulonglong *)(param_1 + 0xb8) = (ulonglong)bVar10;
      *(longlong *)(param_1 + 0xb0) = lVar5;
    }
  }
  puVar2 = local_190;
  local_1c0 = local_198;
  local_1c8 = (undefined1 *)CONCAT71(local_1c8._1_7_,bVar7);
  iVar4 = FUN_7ffa1b03dce0(param_1,local_180,local_168,local_190);
  if (iVar4 == 0) {
    local_1b0 = local_178;
    local_1b8 = local_170;
    local_1c8 = local_168;
    local_1c0 = puVar2;
    iVar4 = FUN_7ffa1b03d2e0(param_1,param_2,lVar5,bVar10);
    if ((iVar4 == 0) && (iVar4 = FUN_7ffa1b03bbc0(param_1,param_2,local_198[0]), iVar4 == 0)) {
      iVar4 = FUN_7ffa1b03a610(param_1,param_2);
    }
  }
LAB_7ffa1b03e3ce:
  lVar6 = 0;
  if (lVar5 != *(longlong *)(param_1 + 0xb0)) {
    lVar6 = lVar5;
  }
  if (lVar6 != 0) {
    if (bVar10 != 0) {
      uVar9 = (ulonglong)bVar10;
      do {
        FUN_7ffa1b039080(lVar8 + lVar6);
        lVar8 = lVar8 + 0x30;
        uVar9 = uVar9 - 1;
      } while (uVar9 != 0);
    }
    thunk_FUN_7ffa1b0c8950(lVar6);
  }
  if (iVar4 != 0) {
    FUN_7ffa1b039080(param_2);
  }
  return iVar4;
}



// ==================================================================
