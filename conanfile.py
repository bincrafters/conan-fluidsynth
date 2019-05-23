# -*- coding: utf-8 -*-

from conans import ConanFile, CMake, tools
import os
import shutil


class FluidSynthConan(ConanFile):
    class CustomOption(object):
        def __init__(self, name,
                     values=None,
                     default=None,
                     cmake_name=None,
                     platforms=None,
                     platforms_blacklist=None,
                     requirements=None):
            self._name = name
            self._values = values or [True, False]
            self._default = default or False
            self._cmake_name = cmake_name or name
            self._cmake_name = "enable-" + self._cmake_name
            self._platforms_whitelist = platforms
            self._platforms_blacklist = platforms_blacklist
            self._requirements = requirements or []

        @property
        def name(self):
            return self._name

        @property
        def cmake_name(self):
            return self._cmake_name

        @property
        def values(self):
            return self._values

        @property
        def default(self):
            return self._default

        @property
        def requirements(self):
            return self._requirements

        def check_platform(self, the_os):
            if self._platforms_whitelist:
                return the_os in self._platforms_whitelist
            elif self._platforms_blacklist:
                return the_os not in self._platforms_blacklist
            else:
                return True

    name = "fluidsynth"
    version = "2.0.5"
    description = "Software synthesizer based on the SoundFont 2 specifications"
    topics = ("conan", "fluidsynth", "soundfont", "midi", "synthesizer")
    url = "https://github.com/bincrafters/conan-fluidsynth"
    homepage = "http://www.fluidsynth.org/"
    author = "Bincrafters <bincrafters@gmail.com>"
    license = "LGPL-2.1-only"
    exports = ["LICENSE.md"]
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake", "pkg_config"
    settings = "os", "arch", "compiler", "build_type"
    conan_options = [CustomOption("shared"),
                     CustomOption("fPIC", default=True, platforms_blacklist=["Windows"]),
                     CustomOption("floats"),
                     CustomOption("fpe-check"),
                     CustomOption("trap-on-check"),
                     CustomOption("portaudio", requirements=["portaudio/v190600.20161030@bincrafters/stable"]),
                     CustomOption("aufile"),
                     CustomOption("dbus"),
                     CustomOption("ipv6", default=True),
                     CustomOption("jack"),
                     CustomOption("ladspa"),
                     CustomOption("libsndfile"),
                     CustomOption("midishare"),
                     CustomOption("opensles"),
                     CustomOption("oboe"),
                     CustomOption("network"),
                     CustomOption("oss"),
                     CustomOption("dsound", default=True, platforms=["Windows"]),
                     CustomOption("waveout", default=True, platforms=["Windows"]),
                     CustomOption("winmidi", default=True, platforms=["Windows"]),
                     CustomOption("sdl2", requirements=["sdl2/2.0.9@bincrafters/stable"]),
                     CustomOption("pkgconfig"),
                     CustomOption("pulseaudio"),
                     CustomOption("readline", requirements=["readline/7.0@bincrafters/stable"]),
                     CustomOption("threads"),
                     CustomOption("lash", platforms=["Linux", "FreeBSD"]),
                     CustomOption("alsa", platforms=["Linux", "FreeBSD"], requirements=["libalsa/1.1.5@conan/stable"]),
                     CustomOption("systemd", platforms=["Linux"]),
                     CustomOption("coreaudio", default=True, platforms=["Macos"]),
                     CustomOption("coremidi", default=True, platforms=["Macos"]),
                     CustomOption("framework", platforms=["Macos"])]

    options = {o.name: o.values for o in conan_options}
    default_options = {o.name: o.default for o in conan_options}
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"
    requires = "glib/2.58.3@bincrafters/stable"

    def configure(self):
        del self.settings.compiler.libcxx

    def build_requirements(self):
        if self.options.pkgconfig:
            if not tools.which("pkg-config"):
                self.build_requires("pkg-config_installer/0.29.2@bincrafters/stable")

    def config_options(self):
        for o in self.conan_options:
            if not o.check_platform(self.settings.os):
                self.options.remove(o.name)

    def requirements(self):
        for o in self.conan_options:
            if o.check_platform(self.settings.os):
                if getattr(self.options, o.name):
                    for r in o.requirements:
                        self.requires(r)

    def source(self):
        source_url = "https://github.com/FluidSynth/fluidsynth"
        tools.get("{0}/archive/v{1}.tar.gz".format(source_url, self.version),
                  sha256="69b244512883491e7e66b4d0151c61a0d6d867d4d2828c732563be0f78abcc51")
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions["enable-debug"] = self.settings.build_type == "Debug"
        cmake.definitions["enable-tests"] = False
        cmake.definitions["LIB_INSTALL_DIR"] = "lib"  # https://github.com/FluidSynth/fluidsynth/issues/476
        for o in self.conan_options:
            if o.check_platform(self.settings.os):
                cmake.definitions[o.cmake_name] = getattr(self.options, o.name)
            else:
                cmake.definitions[o.cmake_name] = False
        cmake.configure(build_folder=self._build_subfolder,
                        source_folder=self._source_subfolder)
        return cmake

    def build(self):
        os.rename(os.path.join(self._source_subfolder, "CMakeLists.txt"),
                  os.path.join(self._source_subfolder, "CMakeListsOriginal.txt"))
        shutil.copy("CMakeLists.txt",
                    os.path.join(self._source_subfolder, "CMakeLists.txt"))

        shutil.move("pcre.pc", "libpcre.pc")
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["fluidsynth"]
        if self.settings.os == "Macos":
            frameworks = []
            if self.options.coreaudio:
                frameworks.extend(["CoreAudio", "AudioToolbox", "CoreServices"])
            if self.options.coremidi:
                frameworks.append("CoreMidi")
            for framework in frameworks:
                self.cpp_info.exelinkflags.append("-framework %s" % framework)
            self.cpp_info.sharedlinkflags = self.cpp_info.exelinkflags
