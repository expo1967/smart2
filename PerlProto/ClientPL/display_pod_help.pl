#!C:\Perl64\bin\perl.exe -w

######################################################################
#
# File      : display_pod_help.pl
#
# Author    : Barry Kimelman
#
# Created   : February 25, 2019
#
# Purpose   : Display POD help for the specified program
#
# Notes     : (none)
#
######################################################################

use strict;
use warnings;

######################################################################
#
# Function  : display_pod_help
#
# Purpose   : Display POD help for the specified program
#
# Inputs    : $_[0] - name of script
#
# Output    : POD help
#
# Returns   : nothing
#
# Example   : display_pod_help($0);
#
# Notes     : (none)
#
######################################################################

sub display_pod_help
{
	my ( $script ) = @_;

	if ( $^O =~ m/MSWin/ ) { # Running under Windows ?
		system("pod2text $script | more");
	} # IF
	else { # running under UNIX
		system("pod2man $script | nroff -man | less -M");
	} # ELSE

	return;
} # end of display_pod_help

1;
