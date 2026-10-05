# Third-party licenses and notices

Constellation project code is Apache-2.0. Bundled third-party components retain their respective licenses and notices; the complete release is the distribution unit. Keep `notices/`, this file, `LICENSE` and `NOTICE` with any redistributed native package. Individual packages contain project license material, not an exhaustive upstream notice collection.

`notices/LICENSE-INDEX.json` maps exact source commits, registry versions/checksums and full retained license texts. The collection covers the complete Cargo locks conservatively; presence in it does not assert that a dependency was linked. `notices/NESTED-NOTICES.json` preserves additional nested notices. Shared license texts are stored once by SHA256 without rewriting their copyrights. Rust's standard-library COPYRIGHT and license files are retained in the same collection.

Native dependencies include permissively licensed Rust code (principally MIT and Apache-2.0, with BSD/ISC/Zlib and other upstream terms recorded verbatim), ring's separately attributed cryptographic implementation and generated arithmetic, and Unicode-derived regex tables. Selected SQLite amalgamations are public-domain upstream material; their Rust wrappers retain their own licenses. The unselected SQLCipher alternative is not a bundled runtime claim. Build/development/cross-platform lock entries are identified as a superset, including entries with no standalone text and no observed Linux build footprint.

Workbench's installed Python code uses the system Python standard library; no external Python library, web JS library, font or icon bundle is installed with that package. System Python, libc, libgcc, systemd, OpenSSL commands and separately pulled central images are runtime dependencies, not bundled redistribution.

The separately served release/reveal pages use Geist Mono (SIL Open Font License 1.1). The font and its full original copyright/license text remain adjacent in `assets/fonts/` on the site. Site screenshots show project-owned Workbench output; their accepted capture manifest preserves provenance. See [distribution scope](DISTRIBUTION.md).
