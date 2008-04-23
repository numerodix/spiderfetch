#!/usr/bin/env ruby
#
# Author: Martin Matusiak <numerodix@gmail.com>
# Licensed under the GNU Public License, version 3.


require "ftools"
require "optparse"
require "tempfile"
require "uri"

$program_name = File.basename __FILE__
$search_string = /<[^>]+?[hH][rR][eE][fF][ ]*=?[ ]*(["'])(.*?)\1[^>]*?>/
$protocol_filter = /^[:alnum:]:\/\//
$pattern = /.*/
$dump_urls = false
$dump_index = false

$wget_tries = 44


## parse args
opts = OptionParser.new do |opts|
	opts.banner = "Usage:  #{$program_name} <url> [<pattern>] [options]\n\n"

	opts.on("--useindex [index_page]", "Use this index instead of fetching") do |v|
		$have_index = v
	end
	opts.on("--dump", "Dump urls, don't fetch") do |v|
		$dump_urls = true
	end
	opts.on("--dumpindex", "Dump index page") do |v|
		$dump_index = true
	end
end 
opts.parse!

if ARGV.empty? and !$have_index
	puts opts.help
	exit 1
else
	$url = ARGV[0]
	ARGV.length > 1 and $pattern = Regexp.compile(ARGV[1])
end


## function to colorize output 
def color c, s
	colors = [:black, :red, :green, :yellow, :blue, :magenta, :cyan, :white]
	col_num = colors.index(c)
	if ENV['TERM'] == "dumb" 
		return s
	else
		return "\e[0;3#{col_num}m#{s}\e[0m"
	end
end

## function to fetch with wget
def wget url, getdata, verbose
	begin
		pre_output = color(:yellow, "\nFetching url #{color(:cyan, url)}... ")
		ok_output = color(:yellow, "===> ") + color(:green, "DONE")
		err_output = color(:yellow, "===> ") + color(:red, "FAILED")

		# build execution string
		if !verbose
			logfile = Tempfile.new $program_name
			logto = "-o #{logfile.path}"
		end
		if getdata
			savefile = Tempfile.new $program_name
			saveto = "-O #{savefile.path}"
		end
		/^https/.match(url) and cert = "--no-check-certificate"
		cmd = "wget -c -t#{$wget_tries} #{logto} #{saveto} #{cert} #{url}"

		# run command
		verbose and puts pre_output
		system(cmd)

		# handle exit value
		if $?.to_i > 0
			# noisy mode
			verbose and puts "\n\n#{err_output}, cmd was:\n#{cmd}"

			# quiet mode
			!verbose and output = "\n" + logfile.open.read
			raise Exception, 
				"#{pre_output}\n#{output}\n#{err_output}, cmd was:\n#{cmd}"
		else
			# noisy mode
			verbose and puts ok_output
		end
		getdata and return savefile.open.read
	ensure
		logfile and logfile.close!
		savefile and savefile.close!
	end
end


## fetch url
begin
	if $have_index
		$content = IO.read $have_index
	else
		$content = wget $url, true, false
	end
	$dump_index and puts $content
rescue Exception => e
	puts e.to_s
	exit 1
end

## find urls in index

# strip off eg. index.html
$url and $url[-1..-1] != "/" and $url = $url.split("/")[0..-2].join("/")

urls = []  
while m = $search_string.match($content)
	s = m.captures[1]
	if !$protocol_filter.match(s)
		begin
			$url and s = URI::join($url + "/", s).to_s
		rescue URI::InvalidURIError
			# silently ignore mangled url
		end
	end
	
	# weed out urls that fail to match pattern
	$pattern.match(s) and urls << s

	$content = $content[m.end(0)-3+m.size..-1]
	#puts "==============", $content, "----------------"
end
urls.uniq!

if $dump_urls 
	puts urls
	exit 0
end

## fetch individual urls
urls.each do |url|
	begin
		wget url, false, true
	rescue Exception => e
		exit 1
	end
end

