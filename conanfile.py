from conans import ConanFile, CMake, tools
import os

required_conan_version = ">=1.33.0"


class FluidSynthConan(ConanFile):
    name = "fluidsynth"
    description = "Software synthesizer based on the SoundFont 2 specifications"
    topics = ("conan", "fluidsynth", "soundfont", "midi", "synthesizer")
    url = "https://github.com/bincrafters/conan-fluidsynth"
    homepage = "http://www.fluidsynth.org"
    license = "LGPL-2.1-only"
    exports_sources = ["CMakeLists.txt", "patches/*"]
    generators = "CMakeToolchain", "pkg_config"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "floats": [True, False],
        "fpe-check": [True, False],
        "trap-on-check": [True, False],
        "portaudio": [True, False],
        "aufile": [True, False],
        "dbus": [True, False],
        "ipv6": [True, False],
        "jack": [True, False],
        "ladspa": [True, False],
        "libsndfile": [True, False],
        "midishare": [True, False],
        "opensles": [True, False],
        "oboe": [True, False],
        "network": [True, False],
        "oss": [True, False],
        "dsound": [True, False],
        "waveout": [True, False],
        "winmidi": [True, False],
        "sdl2": [True, False],
        "pkgconfig": [True, False],
        "pulseaudio": [True, False],
        "readline": [True, False],
        "threads": [True, False],
        "lash": [True, False],
        "alsa": [True, False],
        "systemd": [True, False],
        "coreaudio": [True, False],
        "coremidi": [True, False],
        "framework": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "floats": False,
        "fpe-check": False,
        "trap-on-check": False,
        "portaudio": False,
        "aufile": False,
        "dbus": False,
        "ipv6": True,
        "jack": False,
        "ladspa": False,
        "libsndfile": False,
        "midishare": False,
        "opensles": False,
        "oboe": False,
        "network": True,
        "oss": False,
        "dsound": True,
        "waveout": True,
        "winmidi": True,
        "sdl2": False,
        "pkgconfig": True,
        "pulseaudio": False,
        "readline": False,
        "threads": False,
        "lash": False,
        "alsa": False,
        "systemd": False,
        "coreaudio": True,
        "coremidi": True,
        "framework": True,
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"
    requires = "glib/2.69.0"

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def build_requirements(self):
        if self.options.pkgconfig:
            self.build_requires("pkgconf/1.7.4")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

        if self.settings.os != "Windows": 
            del self.options.dsound
            del self.options.waveout
            del self.options.winmidi
 
        if not self.settings.os in ["Linux", "FreeBSD"]:
            del self.options.lash
            del self.options.alsa

        if self.settings.os != "Linux":
            del self.options.systemd

        if self.settings.os != "Macos":
            del self.options.coreaudio
            del self.options.coremidi
            del self.options.framework

    def requirements(self):
        if self.options.get_safe("portaudio"):
            self.requires("portaudio/v190600.20161030@bincrafters/stable")
        if self.options.get_safe("sdl2"):
            self.requires("sdl2/2.0.14@bincrafters/stable")
        if self.options.get_safe("readline"):
            self.requires("readline/8.0")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version], strip_root=True, destination=self._source_subfolder)

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions["enable-debug"] = self.settings.build_type
        cmake.definitions["enable-tests"] = False
        cmake.definitions["LIB_INSTALL_DIR"] = "lib"  # https://github.com/FluidSynth/fluidsynth/issues/476

        for o in ["floats", "fpe-check", "trap-on-check", "portaudio", "aufile", "dbus", "ipv6", "jack", "ladspa",
        "libsndfile", "midishare", "opensles", "oboe", "network", "oss", "dsound", "waveout", "winmidi", "sdl2", "pkgconfig", "pulseaudio",
        "readline", "threads", "lash", "alsa", "systemd", "coreaudio", "coremidi", "framework"]:
            cmake.definitions["enable-{}".format(o)] = self.options.get_safe(o)
    
        cmake.configure(source_folder=self._source_subfolder, build_folder=self._build_subfolder)
        return cmake

    def build(self):
        with tools.environment_append({"PKG_CONFIG_PATH": self.source_folder}):
            cmake = self._configure_cmake()
            cmake.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        with tools.environment_append({"PKG_CONFIG_PATH": self.source_folder}):
            cmake = self._configure_cmake()
            cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "bin", "pkgconfig"))
        tools.remove_files_by_mask(os.path.join(self.package_folder, "bin"), "msvcp*.dll")
        tools.remove_files_by_mask(os.path.join(self.package_folder, "bin"), "vcruntime*.dll")
        tools.remove_files_by_mask(os.path.join(self.package_folder, "bin"), "concrt*.dll")

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH environment variable: {}".format(bindir))
        self.env_info.PATH.append(bindir)

        if self.settings.compiler == "Visual Studio":
            self.cpp_info.libs = ["fluidsynth" if self.options.shared else "libfluidsynth"]
        else:
            self.cpp_info.libs = ["fluidsynth"]
        if self.settings.os == "Macos":
            self.cpp_info.frameworks.append("Foundation")
            if self.options.coreaudio:
                self.cpp_info.frameworks.extend(["CoreAudio", "AudioToolbox", "CoreServices"])
            if self.options.coremidi:
                self.cpp_info.frameworks.append("CoreMidi")
        if self.settings.os == "Windows":
            if self.options.network:
                self.cpp_info.system_libs.append("ws2_32")
            if self.options.dsound:
                self.cpp_info.system_libs.append("dsound")
            if self.options.winmidi:
                self.cpp_info.system_libs.append("winmm")
