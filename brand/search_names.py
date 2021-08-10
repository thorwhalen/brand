"""Search domain names"""

from brand.base import try_some_cvcvcvs

if __name__ == "__main__":
    from argh import dispatch_command

    dispatch_command(try_some_cvcvcvs)
