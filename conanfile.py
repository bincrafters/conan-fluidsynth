from conans import ConanFile, CMake, tools
import os
import glob


class FluidSynthConan(ConanFile):
    class CustomOption(object):
        def __init__(self, name,
                     values=None,
                     default=None,
                     cmake_name=None,
                     platforms=None,
                     platforms_denylist=None,
                     requirements=None):
            self._name = name
            self._values = values or [True, False]
            self._default = default or False
            self._cmake_name = cmake_name or name
            self._cmake_name = "enable-" + self._cmake_name
            self._platforms_allowlist = platforms
            self._platforms_denylist = platforms_denylist
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
            if self._platforms_allowlist:
                return the_os in self._platforms_allowlist
            elif self._platforms_denylist:
                return the_os not in self._platforms_denylist
            else:
                return True

    name = "fluidsynth"
    description = "Software synthesizer based on the SoundFont 2 specifications"
    topics = ("conan", "fluidsynth", "soundfont", "midi", "synthesizer")
    url = "https://github.com/bincrafters/conan-fluidsynth"
    homepage = "http://www.fluidsynth.org"
    license = "LGPL-2.1-only"
    exports_sources = ["patches/*"]
    generators = "cmake", "pkg_config"
    settings = "os", "arch", "compiler", "build_type"
    conan_options = [CustomOption("floats"),
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
                     CustomOption("network", default=True),
                     CustomOption("oss"),
                     CustomOption("dsound", default=True, platforms=["Windows"]),
                     CustomOption("waveout", default=True, platforms=["Windows"]),
                     CustomOption("winmidi", default=True, platforms=["Windows"]),
                     CustomOption("sdl2", requirements=["sdl2/2.0.12@bincrafters/stable"]),
                     CustomOption("pkgconfig", default=True),
                     CustomOption("pulseaudio"),
                     CustomOption("readline", requirements=["readline/8.0"]),
                     CustomOption("threads"),
                     CustomOption("lash", platforms=["Linux", "FreeBSD"]),
                     CustomOption("alsa", platforms=["Linux", "FreeBSD"], requirements=["libalsa/1.1.9"]),
                     CustomOption("systemd", platforms=["Linux"]),
                     CustomOption("coreaudio", default=True, platforms=["Macos"]),
                     CustomOption("coremidi", default=True, platforms=["Macos"]),
                     CustomOption("framework", platforms=["Macos"])]

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    options.update({o.name: o.values for o in conan_options})
    default_options.update({o.name: o.default for o in conan_options})

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"
    requires = "glib/2.66.2"

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def build_requirements(self):
        if self.options.pkgconfig:
            self.build_requires("pkgconf/1.7.3")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

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
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions["enable-debug"] = self.settings.build_type
        cmake.definitions["enable-tests"] = False
        cmake.definitions["LIB_INSTALL_DIR"] = "lib"  # https://github.com/FluidSynth/fluidsynth/issues/476
        for o in self.conan_options:
            if o.check_platform(self.settings.os):
                cmake.definitions[o.cmake_name] = getattr(self.options, o.name)
            else:
                cmake.definitions[o.cmake_name] = False
        cmake.configure(build_folder=self._build_subfolder, source_folder=self._source_subfolder)
        return cmake

    def _patch_files(self):
        if "patches" in self.conan_data and self.version in self.conan_data["patches"]:
            for patch in self.conan_data["patches"][self.version]:
                tools.patch(**patch)

        cmakelists = os.path.join(self._source_subfolder, "CMakeLists.txt")
        # remove some quirks, let Conan manage them
        tools.replace_in_file(cmakelists, "project ( FluidSynth C )", """project ( FluidSynth C )
include(../conanbuildinfo.cmake)
conan_basic_setup()
        """)

    def build(self):
        self._patch_files()
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
        files = []
        files.extend(glob.glob(os.path.join(self.package_folder, "bin", "msvcp*.dll")))
        files.extend(glob.glob(os.path.join(self.package_folder, "bin", "vcruntime*.dll")))
        files.extend(glob.glob(os.path.join(self.package_folder, "bin", "concrt*.dll")))
        for f in files:
            os.remove(f)

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
