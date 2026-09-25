{
  description = "Folio - Markdown to Beautiful Typst PDF Document Compiler";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }: let
    systems = flake-utils.lib.defaultSystems;
  in
    flake-utils.lib.eachSystem systems (system: let
      pkgs = import nixpkgs {inherit system;};
      lib = pkgs.lib;

      folioPackage = pkgs.python3Packages.buildPythonApplication {
        pname = "folio";
        version = "0.1.0";
        src = ./.;
        pyproject = true;

        build-system = [
          pkgs.python3Packages.setuptools
        ];

        nativeBuildInputs = [
          pkgs.makeWrapper
        ];

        postFixup = ''
          wrapProgram $out/bin/folio \
            --prefix PATH : ${lib.makeBinPath [pkgs.pandoc pkgs.typst]} \
            --set FOLIO_TEMPLATES "$out/${pkgs.python3.sitePackages}/folio/templates"
        '';

        doCheck = false;

        meta = with lib; {
          description = "Markdown to Typst PDF Document Compiler";
          homepage = "https://github.com/SpanishSyntax/Folio";
          license = licenses.mit;
          mainProgram = "folio";
        };
      };
    in {
      packages = {
        default = folioPackage;
        folio = folioPackage;
      };

      apps.default = {
        type = "app";
        program = "${folioPackage}/bin/folio";
      };

      devShells.default = pkgs.mkShell {
        packages = with pkgs; [
          python3
          python3Packages.setuptools
          pandoc
          typst
        ];
      };
    })
    // {
      homeManagerModules = {
        default = self.homeManagerModules.folio;
        folio = {
          config,
          lib,
          pkgs,
          ...
        }: let
          cfg = config.programs.folio;
          system = pkgs.stdenv.hostPlatform.system;
          defaultFolio = self.packages.${system}.default;
        in {
          options.programs.folio = {
            enable = lib.mkEnableOption "Folio - Markdown to Typst PDF Document Compiler";

            package = lib.mkOption {
              type = lib.types.package;
              default = defaultFolio;
              description = "The Folio package to use.";
            };
          };

          config = lib.mkIf cfg.enable {
            home.packages = [cfg.package];
          };
        };
      };
    };
}
