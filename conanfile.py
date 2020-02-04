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
    description = "Software synthesizer based on the SoundFont 2 specifications"
    topics = ("conan", "fluidsynth", "soundfont", "midi", "synthesizer")
    url = "https://github.com/bincrafters/conan-fluidsynth"
    homepage = "http://www.fluidsynth.org/"
    license = "LGPL-2.1-only"
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
                     CustomOption("network", default=True),
                     CustomOption("oss"),
                     CustomOption("dsound", default=True, platforms=["Windows"]),
                     CustomOption("waveout", default=True, platforms=["Windows"]),
                     CustomOption("winmidi", default=True, platforms=["Windows"]),
                     CustomOption("sdl2", requirements=["sdl2/2.0.9@bincrafters/stable"]),
                     CustomOption("pkgconfig", default=True),
                     CustomOption("pulseaudio"),
                     CustomOption("readline", requirements=["readline/7.0@bincrafters/stable"]),
                     CustomOption("threads"),
                     CustomOption("lash", platforms=["Linux", "FreeBSD"]),
                     CustomOption("alsa", platforms=["Linux", "FreeBSD"], requirements=["libalsa/1.1.9"]),
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
        del self.settings.compiler.cppstd

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
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions["enable-debug"] = self.settings.build_type == "Debug"
        cmake.definitions["BUILD_SHARED_LIBS"] = self.options.shared  # fluidsynth forces to True by default
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

    def _patch_files(self):
        cmakelists = os.path.join(self._source_subfolder, "CMakeLists.txt")
        # remove some quirks, let conan manage them
        tools.replace_in_file(cmakelists, 'string ( REGEX REPLACE "/MD" "/MT" ${flag_var} "${${flag_var}}" )', '')
        tools.replace_in_file(cmakelists, 'set ( CMAKE_POSITION_INDEPENDENT_CODE ${BUILD_SHARED_LIBS} )', '')
        # FIXME : components
        shutil.copy("glib.pc", "glib-2.0.pc")
        shutil.copy("glib.pc", "gthread-2.0.pc")

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

    def package_info(self):
        if self.settings.compiler == "Visual Studio":
            self.cpp_info.libs = ["fluidsynth" if self.options.shared else "libfluidsynth"]
        else:
            self.cpp_info.libs = ["fluidsynth"]
        if self.settings.os == "Macos":
            if self.options.coreaudio:
                self.cpp_info.frameworks.extend(
                    ["CoreAudio", "AudioToolbox", "CoreServices"])
            if self.options.coremidi:
                self.cpp_info.frameworks.append("CoreMidi")
        if self.settings.os == "Windows":
            if self.options.network:
                self.cpp_info.system_libs.append("ws2_32")
            if self.options.dsound:
                self.cpp_info.system_libs.append("dsound")
            if self.options.winmidi:
                self.cpp_info.system_libs.append("winmm")
