#!/usr/bin/env ruby


require "ftools"
require "net/http"
require "optparse"
require "tempfile"
require "uri"

$program_name = File.basename __FILE__
$search_string = /<[ ]*[aA][ ]+[hH][rR][eE][fF][ ]*=[ ]*\"(.*?)\"[^>]*?>/
$protocol_filter = /^(http|https|ftp):\/\//
$pattern = /.*/
$dump_urls = false

$wget_tries = 1

## parse args
opts = OptionParser.new do |opts|
	opts.banner = "Usage:  #{$program_name} <url> [<pattern>] [options]\n\n"

	opts.on("--dump", "Dump urls, don't fetch") do |v|
		$dump_urls = true
	end
end 
opts.parse!

if ARGV.empty?
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
		process = IO.popen cmd
		trap('INT') { 
			puts color(:red, "\n>>>>> Got INT")
			#process.close
			puts color(:red, "\n>>>>> Got INT")
			exit 1
		}
		process.eof?	# block until process completes
		process.close
		if $?.to_i > 0
			output = logfile.open.read
			print "Fetching url #{color(:yellow, url)}... "
			puts color(:red, "FAILED"), "#{cmd}\n#{output}"
			#raise Exception
		end
		getdata and return savefile.open.read
	ensure
		logfile and logfile.close!
		savefile and savefile.close!
	end
end


## fetch url
begin
	content = wget $url, true, false
	#puts content
rescue Exception => e
	exit 1
end

## find urls in index
#puts content
urls = []
while m = $search_string.match(content)
	s = m.captures[0]
	if !$protocol_filter.match(s)
		s = URI::join($url + '/', s).to_s
	end
	
	# weed out urls that fail to match pattern
	$pattern.match(s) and s[-1..-1] != '/' and urls << s

	#puts m.end(0), m.size
	content = content[m.end(0)-3+m.size..-1]
	#puts "==============", content, "----------------"
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
		retry
	end
end

