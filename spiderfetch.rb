#!/usr/bin/env ruby
#
# Author: Martin Matusiak <numerodix@gmail.com>
# Licensed under the GNU Public License, version 3.


require "ftools"
require "optparse"
require "tempfile"
require "uri"

$program_name = File.basename __FILE__
$program_path = File.dirname __FILE__

$protocol_filter = /^[a-zA-Z]+:\/\//
$pattern = /.*/

$host_filter = false
$fetch_urls = false
$dump_urls = false
$dump_index = false
$dump_color = false

$colors = [:black, :red, :green, :yellow, :blue, :magenta, :cyan, :white]

$wget_tries = 44
# this should open some doors for us (IE7/Vista)
$wget_ua = '--user-agent "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)"'


in_tag = /<[^>]+?(?:[hH][rR][eE][fF]|[sS][rR][cC])[ ]*=?[ ]*(["'`])(.*?)\1[^>]*?>/m
uri_match = /[A-Za-z][A-Za-z0-9+.-]{1,120}:\/\/(([A-Za-z0-9$_.+!*,;\/?:@&~(){}\[\]=-])|%[A-Fa-f0-9]{2}){1,333}(#([a-zA-Z0-9][a-zA-Z0-9 $_.+!*,;\/?:@&~(){}\[\]=%-]{0,1000}))?/m

$regexs = [ 
	{:regex=>in_tag, :group=>2},
	{:regex=>uri_match, :group=>0},
	{:regex=>URI::regexp, :group=>0},
][0..5]	  # we only have 6 colors, let's not crash on array out of bounds


## parse args
opts = OptionParser.new do |opts|
	opts.banner = "Usage:  #{$program_name} <url> [<pattern>] [options]\n\n"

	opts.on("--useindex index_page", "Use this index file instead of fetching") do |v|
		$index_file = v
	end
	opts.on("--recipe recipe", "Use this spidering recipe") do |v|
		$recipe_file = v
	end
	opts.on("--host", "Only spider this host") do |v|
		$host_filter = true
	end
	opts.on("--fetch", "Fetch urls, don't dump") do |v|
		$fetch_urls = true
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

if ARGV.empty? and !$index_file
	STDERR.puts opts.help
	exit 1
else
	$url = ARGV[0]
	ARGV.length > 1 and $pattern = Regexp.compile(ARGV[1])
end


## function to colorize output 
def color c, s, *opt
	col_num = $colors.index(c)
	if ENV['TERM'] == "dumb" 
		return s
	else
		b="0"
		opt and opt[0] and opt[0][:bold] and b="1"
		return "\e[#{b};3#{col_num}m#{s}\e[0m"
	end
end

def color_code c, code, *opt
	s = color(c, "z", *opt)
	if code and code == -1
		return Regexp.new("^(.*)z").match(s)[1].to_s
	elsif code == 1
		return Regexp.new("z(.*)$").match(s)[1].to_s
	end
end

## function to fetch with wget
def wget url, getdata, verbose, action
	begin
		action = "#{action}::"
		noisy = {
			:pre=> color(:yellow, "\nFetching url #{color(:cyan, url)} ... "),
			:post=> "\n\n#{color(:yellow, "===> %s")}\n" }
		quiet = {
			:pre=> "#{action}  #{url}\r",
			:post=> "#{action}  %s  #{url}\n" }

		# build execution string
		logto = "-o /dev/null" unless verbose
		if getdata
			savefile = Tempfile.new $program_name
			saveto = "-O #{savefile.path}"
		end
		cert = "--no-check-certificate"
		cmd = "wget #{logto} #{saveto} #{$wget_ua} #{cert} -k -c -t#{$wget_tries} '#{url}' 2>&1"

		# run command
		STDERR.puts noisy[:pre] if verbose
		STDERR.print quiet[:pre] unless verbose
		system(cmd)

		# handle exit value
		wget_exit = $?.to_i
		if [2, 130].member? wget_exit
			raise Exception, color(:yellow, "\nKilled")
		elsif wget_exit > 0
			quiet[:status] = color(:red, "fail")
			noisy[:status] = "#{color(:red, "FAILED")}, cmd was:\n#{cmd}"
		else
			quiet[:status] = color(:green, "done")
			noisy[:status] = color(:green, "DONE")
		end
		STDERR.printf noisy[:post], noisy[:status] if verbose
		STDERR.printf quiet[:post], quiet[:status] unless verbose

		getdata and return savefile.open.read
	ensure
		savefile and savefile.close!
	end
end

def fetch_url url, read_file, verbose, action
	begin
		content = wget url, read_file, verbose, action
	rescue Exception => e
		STDERR.puts e.to_s
		exit 1
	end
	return content
end

def fetch_index url
	return fetch_url(url, true, false, "spider")
end

def fetch_file url
	return fetch_url(url, false, true, "fetch")
end

def findall regex, group, s, pattern_filter
	cs = 0

	matches = []
	while m = regex.match(s[cs..-1])

		match_start = cs + m.begin(group)
		match_end = cs + m.end(group)

		if pattern_filter.match m[group] and $protocol_filter.match m[group]
			matches << {:start=>match_start, :end=>match_end}
		end

		cs = match_end
	end

	return matches
end

def implode_regexs regexs
	regexs.compact!
	regexs.map!{|r| if r.class == Regexp then r.to_s else r end  }
	s = "("
	s += regexs[0..-2].collect{|r| r + "|" }.join("")
	s += regexs[-1]
	s += ")"
	return Regexp.new(s)
end

def explode_findings pattern_keys, rule, findings
	regexs = pattern_keys.collect{|k| Regexp.new rule[k] if rule[k] }
	pairs = pattern_keys.zip(regexs)
	pairs.collect!{|pair| if pair[1] then pair end }.compact! # kill nulls

	keys = pairs.collect{|pair| pair[0] }
	regexs = pairs.collect{|pair| pair[1] }

	arr = regexs.collect{|r| findings.collect{|f| if r.match(f) then f end }.compact}
	hash = {}
	keys.zip(arr).each{|pair| hash[pair[0]] = pair[1] }
	return hash
end

def format markers, s
	markers.empty? and return color(:white, s)

	sf = ""

	stack = []
	cursor = 0
	markers.each do |marker|
		orig_sym = marker[:color] != nil ? -1 : 1

		sym = orig_sym
		col = marker[:color]
		col_bold = false

		if orig_sym == -1 and stack.length > 0   # adding color on top of color
			col_bold = true
		elsif orig_sym == 1 and stack.length > 1   # ending color with color below
			col = stack[stack.length-2]
			sym = -1
			stack.length > 2 and col_bold = true   # two or more layers, make it bold
		end

		orig_sym == -1 and stack << marker[:color]
		orig_sym == 1 and stack.pop

		sf += s[cursor..marker[:marker]-1] + color_code(col, sym, {:bold=>col_bold})
		cursor = marker[:marker]
	end
	sf += s[markers[-1][:marker]..-1]	# write segment after last match
	return sf
end

def collect_find regexs, s, pattern_filter, fmt
	colors = [:green, :yellow, :cyan, :blue, :magenta, :red]

	matches = []
	regexs.each do |regex|
		ms = findall(regex[:regex], regex[:group], s, pattern_filter)
		ms = ms.each { |m| m[:color] = colors[regexs.index(regex)] ;
			m[:fallback] = regexs.index(regex) }   # extra sort parameter
		matches += ms
	end
	# sort to get longest match first, to wrap coloring around shorter
	matches.sort! { |m1, m2| 
		[m1[:start],m2[:end],m2[:fallback]] <=> 
		[m2[:start],m1[:end],m1[:fallback]] }

	urls = []
	matches.each do |match|
		urls << s[match[:start]..match[:end]-1]
	end
	urls.uniq!

	if fmt
		markers = []
		matches.each do |match|
			markers << {:marker=>match[:start], :color=>match[:color], 
				:serial=>matches.index(match)}   # for later sorting by longest match
			markers << {:marker=>match[:end], :serial=>matches.index(match)}
		end
		markers.sort! { |m1, m2| [m1[:marker],m1[:serial]] <=> [m2[:marker],m2[:serial]] }
		formatted = format(markers, s)
	end

	return {:urls=>urls, :formatted=>formatted}
end

def get_host_regex url
	begin
		raise Exception, "Url is empty" unless url

		u = URI.parse $url
		password = ":" + u.password if u.password
		user = ""
		user = u.user + password + "@" if u.user and u.password
		user = u.user + "@" if u.user
		host = u.scheme + "://" + user + u.host
		return Regexp.new("^" + host)
	rescue Exception => e
		STDERR.puts color(:red, "ERROR::") + "  Failed to parse url '#{url}'"
		STDERR.puts e.to_s, e.backtrace
		exit 1
	end
end

def load_recipe path
	begin
		require "#{$program_path}/#{path}"
		return Recipe::RECIPE
	rescue Exception => e
		STDERR.puts color(:red, "ERROR::") + "  Failed to load recipe #{path}"
		STDERR.puts e.to_s, e.backtrace
		exit 1
	end
end

def get_default_recipe pattern
	action = :fetch
	action = :dump if $dump_urls
	action = :dumpindex if $dump_index 
	action = :dumpcolor if $dump_color 
	return [{action=>pattern}]
end



$host_regex = get_host_regex $url if $host_filter

recipe = load_recipe $recipe_file if $recipe_file
recipe = get_default_recipe $pattern if !recipe
recipe[0][:useindex] = true if $index_file

cache = { :fetch => [], :spider => [$url], :dump => [] }
data  = { :fetch => [], :spider => [$url], :dump => [] }
while rule = recipe[0] and recipe = recipe[1..-1]
	depth = rule[:depth] ? rule[:depth] : 1

	## cmd line action override
	if $fetch_urls and rule[:dump]
		rule[:fetch] = rule[:dump]
		rule.delete :dump
	elsif $dump_urls and rule[:fetch]
		rule[:dump] = rule[:fetch]
		rule.delete :fetch
	end

	while !data[:spider].empty? and (depth > 0 or depth < 0)
		depth -= 1

		## fetch and read index file
		if rule[:useindex]
			content = IO.read $index_file
		else
			content = data[:spider].collect { |url| fetch_index url }.join("\n")
		end

		## set up and combine patterns for matching
		pattern_keys = [:fetch, :spider, :dump, :dumpindex, :dumpcolor]
		pattern_merged = implode_regexs pattern_keys.collect{|k| rule[k] }

		## do matching on every pattern in rule
		findings = collect_find($regexs, content, pattern_merged, rule[:dumpcolor])

		## filter all matches into findings by pattern
		found = explode_findings pattern_keys, rule, findings[:urls]

		## apply host filter
		found[:spider].collect!{|u| u if $host_regex.match(u)}.compact! if $host_filter

		## update data and cache values with new findings
		[:fetch, :spider, :dump].each { |action|
			if found[action]
				data[action] = found[action] - cache[action]
				cache[action] += data[action]
			else
				data[action] = []
			end
		}

		if rule[:dumpcolor]
			STDOUT.puts findings[:formatted]
			exit 0
		elsif rule[:dumpindex]
			STDOUT.puts content
			exit 0
		elsif rule[:dump]
			STDOUT.puts data[:dump]
		elsif rule[:fetch]
			data[:fetch].each do |url|
				fetch_file url
			end
		end

	end
end

