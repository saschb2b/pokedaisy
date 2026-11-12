#!/bin/bash
# PokeDaisy as a PortMaster port (ROCKNIX, Knulli, muOS, AmberELEC and the other firmwares that
# run PortMaster): PortMaster's usual launcher. Put this file and the pokedaisy/ folder in your
# ports folder, and your games in pokedaisy/roms/. Tried on ROCKNIX (a Retroid Pocket Nova).

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}
if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi
# shellcheck source=/dev/null
source "$controlfolder/control.txt"
# shellcheck source=/dev/null
[ -f "$controlfolder/mod_$CFW_NAME.txt" ] && source "$controlfolder/mod_$CFW_NAME.txt"
get_controls

# control.txt sets $directory (the firmware's roms root) and the controller mapping.
# shellcheck disable=SC2154
GAMEDIR="/$directory/ports/pokedaisy"
cd "$GAMEDIR" || exit 1
mkdir -p roms saves states
: > "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

export POCKET_FULLSCREEN=1
# shellcheck disable=SC2154
export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"
# gptokeyb gives PortMaster's exit hotkey; the game list's B and the game menu's quit work too.
if [ -n "$GPTOKEYB" ]; then
  $GPTOKEYB "pokedaisy-linux" &
fi
# DS games: with the libretro DS core (linux/libretro-ds) in cores/ and RetroArch on the firmware, the game list hands
# a .nds over (--nds-handoff) and RetroArch runs it in that core, its saves and states in this port's own folders
# (saves/<game>.srm) whatever RetroArch's own settings say, and nothing of this written back to them.
DSCORE="$GAMEDIR/cores/pokedaisy_ds_libretro.so"
HANDOFF="$GAMEDIR/.nds-handoff"
if [ -f "$DSCORE" ] && command -v retroarch > /dev/null; then
  printf '%s = "%s"\n' savefile_directory "$GAMEDIR/saves" savestate_directory "$GAMEDIR/states" \
    savefiles_in_content_dir false savestates_in_content_dir false \
    sort_savefiles_enable false sort_savefiles_by_content_enable false \
    sort_savestates_enable false sort_savestates_by_content_enable false \
    config_save_on_exit false global_core_options true core_options_path "$GAMEDIR/retroarch-ds-options.cfg" \
    > "$GAMEDIR/retroarch-ds.cfg"
  # The party HUD starts on, as in the app (the companion's own SETTINGS, once changed, have the say).
  [ -f "$GAMEDIR/retroarch-ds-options.cfg" ] || echo 'pokedaisy_ds_hud = "enabled"' > "$GAMEDIR/retroarch-ds-options.cfg"
  while :; do
    rm -f "$HANDOFF"
    ./pokedaisy-linux --data "$GAMEDIR" --nds-handoff "$HANDOFF"
    [ -s "$HANDOFF" ] || break
    retroarch -L "$DSCORE" --appendconfig "$GAMEDIR/retroarch-ds.cfg" "$(cat "$HANDOFF")"
  done
  rm -f "$HANDOFF"
else
  ./pokedaisy-linux --data "$GAMEDIR"
fi

if declare -f pm_finish > /dev/null; then
  pm_finish
else
  $ESUDO kill -9 "$(pidof gptokeyb)" 2> /dev/null
  printf "\033c" > /dev/tty0
fi
