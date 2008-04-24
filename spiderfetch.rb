#!/usr/bin/env ruby
#
# Author: Martin Matusiak <numerodix@gmail.com>
# Licensed under the GNU Public License, version 3.


require "ftools"
require "optparse"
require "tempfile"
require "uri"

$program_name = File.basename __FILE__
$protocol_filter = /^[:alnum:]:\/\//
$pattern = /.*/
$dump_urls = false
$dump_index = false
$dump_color = false

$colors = [:black, :red, :green, :yellow, :blue, :magenta, :cyan, :white]

$wget_tries = 44
$wget_ua = '--user-agent ""'  # work around picky hosts


in_tag = /<[^>]+?(?:[hH][rR][eE][fF]|[sS][rR][cC])[ ]*=?[ ]*(["'`])(.*?)\1[^>]*?>/
uri_match = /([A-Za-z][A-Za-z0-9+.-]{1,120}:\/\/(([A-Za-z0-9$_.+!*,;\/?:@&~(){}\[\]=-])|%[A-Fa-f0-9]{2}){1,333}(#([a-zA-Z0-9][a-zA-Z0-9 $_.+!*,;\/?:@&~(){}\[\]=%-]{0,1000}))?)/m

$regexs = [ 
	{:regex=>in_tag, :group=>2},
	{:regex=>uri_match, :group=>1},
]


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
	opts.on("--dumpcolor", "Dump index page formatted to show matches") do |v|
		$dump_color = true
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
def color c, s, *bold
	col_num = $colors.index(c)
	if ENV['TERM'] == "dumb" 
		return s
	else
		b="0"
		bold[0] and b="1"
		return "\e[#{b};3#{col_num}m#{s}\e[0m"
	end
end

def color_code c, code, *bold
	s = color(c, "z", *bold)
	if code and code == -1
		return Regexp.new("^(.*)z").match(s)[1].to_s
	elsif code == 1
		return Regexp.new("z(.*)$").match(s)[1].to_s
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
		cert = "--no-check-certificate"
		cmd = "wget #{$wget_ua} #{cert} -k -c -t#{$wget_tries} #{logto} #{saveto} #{url}"

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

def findall regex, group, s
	cs = 0

	matches = []
	while m = regex.match(s[cs..-1])

		match_start = cs + m.begin(group)
		match_end = cs + m.end(group)

		matches << {:start=>match_start, :end=>match_end}

#		require 'pp'
#		PP.singleline_pp [m.offset(group), (m.end(group)-m.begin(group)), m[group].length, m[group]]
#		puts
#		PP.singleline_pp [[match_start, match_end], (match_end-match_start), m[group].length, m[group]]
#		puts
#		PP.singleline_pp [s[match_start..match_end-1].length, s[match_start..match_end-1]]
#		puts "\n\n"

		cs = match_end
	end

	return matches
end

def format markers, s
	markers.empty? and return color(:red, s)

	sf = ""

	stack = []
	cursor = 0
	markers.each do |marker|
		orig_code = marker[:color] != nil ? -1 : 1

		code = orig_code
		col = marker[:color]
		col_bold = false

		if orig_code == 1 and stack.length > 1
			col = stack[stack.length-2]
			code = -1
			stack.length > 2 and col_bold = true
		elsif orig_code == -1 and stack.length > 0
			col_bold = true
		end
#		p [marker[:marker], [code, orig_code], [marker[:color], col], stack] ; puts

		orig_code == -1 and stack << marker[:color]
		orig_code == 1 and stack.pop

		sf += s[cursor..marker[:marker]-1] + color_code(col, code, col_bold)
		cursor = marker[:marker]
	end
	sf += s[markers[-1][:marker]..-1]	# write segment after last match
	return sf
end

def collect_find regexs, s
	colors = [:green, :yellow, :cyan, :blue, :magenta, :white, :red]

	matches = []
	regexs.each do |regex|
		ms = findall(regex[:regex], regex[:group], s)
		ms = ms.each { |m| m[:color] = colors[regexs.index(regex)] }
		matches += ms
	end
	# sort to get longest match first, to wrap coloring around shorter
	matches.sort! { |m1, m2| [m1[:start],m2[:end]] <=> [m2[:start],m1[:end]] }

	urls = []
	matches.each do |match|
		urls << s[match[:start]..match[:end]-1]
	end

	markers = []
	matches.each do |match|
		markers << {:marker=>match[:start], :color=>match[:color], 
			:serial=>matches.index(match)}   # for later sorting by longest match
		markers << {:marker=>match[:end], :serial=>matches.index(match)}
	end
	markers.sort! { |m1, m2| [m1[:marker],m1[:serial]] <=> [m2[:marker],m2[:serial]] }
	formatted = format(markers, s)

	return {:matches=>matches, :urls=>urls, :formatted=>formatted}
end



## fetch url
begin
	if $have_index
		$content = IO.read $have_index
	else
		$content = wget $url, true, false
	end
rescue Exception => e
	puts e.to_s
	exit 1
end

## find urls in index

findings = collect_find $regexs, $content

urls = findings[:urls]
urls.uniq!

formatted = findings[:formatted]
if $dump_color 
	puts formatted
	exit 0
elsif $dump_index 
	puts $content
	exit 0
elsif $dump_urls 
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

