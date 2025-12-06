#!/usr/bin/perl
use strict;
use warnings;
use File::Glob ':glob';    # To work with file paths
use HTML::Parser;         # To handle HTML/XML parsing

# Folder paths
my $input_folder = 'INPUT';
my $output_folder = 'OUTPUT';
my $lexicon_file = 'lexicon_only.txt';

# Function to clear the OUTPUT folder
sub clear_output_folder {
    my ($folder_path) = @_;
    my @files = bsd_glob("$folder_path/*");    # Get all files in the folder
    foreach my $file (@files) {
        unlink $file if -f $file;              # Delete each file
    }
}

# Function to read the lexicon file into an array
sub read_lexicon {
    my ($lexicon_file) = @_;
    open my $fh, '<', $lexicon_file or die "Could not open '$lexicon_file' $!";
    my @lexicon_words = map { chomp; lc($_) } <$fh>;    # Lowercase lexicon words
    close $fh;
    return \@lexicon_words;
}

# Preprocess and process text while skipping tags
sub process_text {
    my ($text, $lexicon_words) = @_;
    my $processed_text = '';
    
    my $parser = HTML::Parser->new(api_version => 3);
    
    $parser->handler(start => sub {
        my ($tagname, $attr) = @_;
        $processed_text .= "<$tagname";
        while (my ($key, $value) = each %$attr) {
            $processed_text .= " $key=\"$value\"";
        }
        $processed_text .= ">";
    }, "tagname,attr");

    $parser->handler(end => sub {
        my ($tagname) = @_;
        $processed_text .= "</$tagname>";
    }, "tagname");

    $parser->handler(text => sub {
        my ($text) = @_;
        # Process text content only, skipping tags
        $text = preprocess_text($text);
        $text =~ s/(\S+)/process_word($1, $lexicon_words)/ge;
        $processed_text .= $text;
    }, "text");

    $parser->parse($text);
    return $processed_text;
}

# Function to handle quotes and prefix 'ku'
sub preprocess_text {
    my ($text) = @_;
    
    # Replace words beginning with quote followed by 'ku' with ' ku'
    $text =~ s/(['"]\s*)ku/$1 ku/g;

    return $text;
}

# Function to process each word
sub process_word {
    my ($word, $lexicon_words) = @_;

    # Save and remove punctuation attached to the end of the word
    my $punctuation = '';
    if ($word =~ /([!?.,\'"\(\)\[\]\{\}:;...\/\\~_-])$/) {
        $punctuation = $1;
        $word =~ s/[!?.,\'"\(\)\[\]\{\}:;...\/\\~_-]$//;
    }

    my $original_word = $word;
    my $lower_word = lc($word);

    # Check if the full word (with 'nya', 'mu', 'ku') is in the lexicon
    if (grep { $_ eq $lower_word } @$lexicon_words) {
        return $original_word . $punctuation;    # No split if full match is found
    }

    # If the word ends with 'nya', check the root word
    if ($lower_word =~ /nya$/) {
        my $root_word = substr($word, 0, -3);
        my $lower_root_word = lc($root_word);

        # Check if the root word is in the lexicon
        if (grep { $_ eq $lower_root_word } @$lexicon_words) {
            return $root_word . ' -nya ' . $punctuation;    # Add space before punctuation
        }
    }

    # If the word ends with 'mu', check the root word
    if ($lower_word =~ /mu$/) {
        my $root_word = substr($word, 0, -2);
        my $lower_root_word = lc($root_word);

        # Check if the root word is in the lexicon
        if (grep { $_ eq $lower_root_word } @$lexicon_words) {
            return $root_word . ' -mu ' . $punctuation;    # Add space before punctuation
        }
    }

    # If the word ends with 'ku', check the root word
    if ($lower_word =~ /ku$/) {
        my $root_word = substr($word, 0, -2);
        my $lower_root_word = lc($root_word);

        # Check if the root word is in the lexicon
        if (grep { $_ eq $lower_root_word } @$lexicon_words) {
            return $root_word . ' -ku ' . $punctuation;    # Add space before punctuation
        }
    }

    # If the word starts with 'ku', check the root word
    if ($lower_word =~ /^ku(.+)/) {
        my $root_word = $1;    # Everything after 'ku'
        my $lower_root_word = lc($root_word);

        # Check if the root word is in the lexicon
        if (grep { $_ eq $lower_root_word } @$lexicon_words) {
            return 'ku- ' . $root_word . ' ' . $punctuation;    # Add space after 'ku-' and preserve original case
        }
    }

    # If no condition is met, return the word as is
    return $original_word . $punctuation;
}

# Function to process each file
sub process_file {
    my ($file_path, $lexicon_words) = @_;

    open my $fh, '<', $file_path or die "Could not open file '$file_path': $!";
    my $file_content = do { local $/; <$fh> };    # Read the entire file content
    close $fh;

    # Process text, skipping tags
    my $processed_content = process_text($file_content, $lexicon_words);

    return $processed_content;
}

# Clear the OUTPUT folder if it has content
clear_output_folder($output_folder);

# Read lexicon words in lowercase
my $lexicon_words = read_lexicon($lexicon_file);

# Read all files in the INPUT folder and process them
my @input_files = bsd_glob("$input_folder/*");
foreach my $input_file (@input_files) {
    if (-f $input_file) {
        my $processed_content = process_file($input_file, $lexicon_words);
        my $output_file = "$output_folder/" . (split('/', $input_file))[-1];
        open my $out_fh, '>', $output_file or die "Could not open '$output_file': $!";
        print $out_fh $processed_content;
        close $out_fh;
    }
}

print "Processing complete.\n";
