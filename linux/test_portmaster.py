"""Run the PortMaster launcher (linux/portmaster/PokeDaisy.sh) from a real --portmaster package against a
stand-in PortMaster: its control.txt (the roms root, the controller mapping, gptokeyb, pm_finish) found
through $XDG_DATA_HOME, as on a firmware that keeps PortMaster there. No device, no firmware.

Twice: the plain package, then one with the libretro DS core (--ds-core) on a firmware with RetroArch, where the
game list runs for a hand-off and DS saves are kept in the port's own folders."""
from pathlib import Path
import os, signal, subprocess, sys, tempfile, time, zipfile
binary = Path(sys.argv[1]).resolve()
arch = {62: 'x86_64', 183: 'aarch64'}[int.from_bytes(binary.read_bytes()[18:20], 'little')]
package = Path(__file__).with_name('package.py')


def launch(d, ds_core):
    d.mkdir()
    extra = []
    if ds_core:
        core = d / 'core.so'
        core.write_bytes(binary.read_bytes()[:64])  # a stand-in: an ELF header for the binary's target
        extra = ['--ds-core', str(core)]
    subprocess.run([sys.executable, str(package), '--portmaster', *extra, str(binary), str(d / 'out')], check=True,
                   capture_output=True)
    ports = d / 'roms' / 'ports'
    ports.mkdir(parents=True)
    with zipfile.ZipFile(d / 'out' / f'pokedaisy-portmaster-{arch}.zip') as z:
        z.extractall(d / 'out')
    for f in (d / 'out' / f'pokedaisy-portmaster-{arch}').iterdir():
        f.rename(ports / f.name)
    for f in (ports / 'PokeDaisy.sh', ports / 'pokedaisy' / 'pokedaisy-linux'):
        f.chmod(0o755)  # zipfile doesn't restore the mode; PortMaster's installer does
    pm = d / 'xdg' / 'PortMaster'
    pm.mkdir(parents=True)
    (pm / 'gptokeyb').write_text('#!/bin/sh\necho "gptokeyb $*" > "$GPTOKEYB_MARK"\n')
    (pm / 'gptokeyb').chmod(0o755)
    (pm / 'control.txt').write_text(
        f'directory="{str(d / "roms").lstrip("/")}"\n'
        'get_controls() { sdl_controllerconfig="00000000000000000000000000000000,PortMaster test pad,a:b0,b:b1"; }\n'
        f'GPTOKEYB="{pm / "gptokeyb"}"\nESUDO=""\nCFW_NAME=test\n'
        'pm_finish() { :; }\n')
    env = dict(os.environ, XDG_DATA_HOME=str(d / 'xdg'), GPTOKEYB_MARK=str(d / 'gptokeyb.ran'),
               SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', SDL_RENDER_DRIVER='software')
    if ds_core:  # the firmware's RetroArch: it must not start before a DS game is picked
        (d / 'bin').mkdir()
        (d / 'bin' / 'retroarch').write_text(f'#!/bin/sh\necho "$*" > "{d / "retroarch.ran"}"\n')
        (d / 'bin' / 'retroarch').chmod(0o755)
        env['PATH'] = f'{d / "bin"}:{env["PATH"]}'
    p = subprocess.Popen(['bash', str(ports / 'PokeDaisy.sh')], env=env, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log = ports / 'pokedaisy' / 'log.txt'
    for _ in range(100):  # the game list is up once SDL has opened its window
        if log.exists() and 'Video backend' in log.read_text():
            break
        time.sleep(0.1)
    os.killpg(p.pid, signal.SIGTERM)
    p.wait(timeout=10)
    text = log.read_text()
    assert 'Video backend' in text, text
    assert all((ports / 'pokedaisy' / n).is_dir() for n in ('roms', 'saves', 'states'))
    assert (d / 'gptokeyb.ran').read_text().strip() == 'gptokeyb pokedaisy-linux'
    return ports / 'pokedaisy'


with tempfile.TemporaryDirectory(prefix='pd-portmaster-') as d:
    port = launch(Path(d) / 'plain', False)
    assert not (port / 'retroarch-ds.cfg').exists() and not (port / 'cores').exists()
    port = launch(Path(d) / 'ds', True)
    assert (port / 'cores' / 'pokedaisy_ds_libretro.so').is_file()
    assert (port / 'licenses' / 'DSperate-GPL-3.0.txt').is_file()
    cfg = (port / 'retroarch-ds.cfg').read_text()
    assert f'savefile_directory = "{port / "saves"}"' in cfg and 'savefiles_in_content_dir = "false"' in cfg, cfg
    assert 'config_save_on_exit = "false"' in cfg, cfg
    assert f'core_options_path = "{port / "retroarch-ds-options.cfg"}"' in cfg, cfg
    assert (port / 'retroarch-ds-options.cfg').read_text().strip() == 'pokedaisy_ds_hud = "enabled"'
    assert not (Path(d) / 'ds' / 'retroarch.ran').exists() and not (port / '.nds-handoff').exists()
print('PASS PortMaster launcher: control.txt found, the port folder made, gptokeyb started, the game list up; '
      'with the DS core, its RetroArch settings written and RetroArch left alone until a DS game is picked')
