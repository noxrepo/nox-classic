<html>

<head>
<!--
<meta http-equiv="expires" content="-1">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="cache-Control" content="no-cache">
-->

<title>Librarian - Nox Archive Browsing System</title>

<style type="text/css">
table
{
    font-family: monospace;
    font-size: 8pt;
}

select
{
    font-family: monospace;
    font-size: 8pt;
}

input
{
    font-family: monospace;
    font-size: 8pt;
}

b
{
    font-size: 10pt;
}
</style>

<script type="text/javascript">
<!--
<?php
    $sections = array("profile" => array("user", "machine", "run_date"),
                  "build" => array("commit", "last_author", "build_date"),
                  "test" => array("configuration", "command", "packets", "rules", "policies"),
                  "result" => array("total", "user", "system"),
                  "variables" => array("independent", "dependent"));
?>

function check_exact(item, exact)
{
    exact = document.getElementsByName(exact)[0]
    if (item.options[item.selectedIndex].value == "Exact")
    {
        exact.style.display = "block"
    }
    else
    {
        exact.style.display = "none"
    }
}

function init()
{
<?php

function nab_info($thing)
{
    return ($_POST[$thing] == "Exact")?($_POST[$thing . "_exact"]):($_POST[$thing]);
}

function nab_exact($thing)
{
    return ($_POST[$thing . "_exact"] != "None")?($_POST[$thing . "_exact"]):("");
}

function select_if($have,$got)
{
    return ($have == $got)?(" selected"):("");
}

$dir = '/home/awesome/base_directory/asena/nox/src/scripts/buildtest/';
$command = $dir . 'lookup.py';
foreach ($sections as $section=>$items)
{
    foreach ($items as $item)
    {
        $command = $command . ' ' .  nab_info($section . "_" . $item);
    }
}
$command = $command . ' 2>&1';  // This is necessary to see any errors

exec($command);

// Debugging
/**/
echo "//" . $command . "\n";
echo "//" . exec($command, $a, $retval) . "\n";
foreach ($a as $line)
{
    echo "//" . $line . "\n";
}
echo "//" . $retval . "\n";
/**/

    function init_display($name)
    {
        echo "    check_exact(document.graph_selection." . $name . ",\"" . $name . "_exact\")\n";
    }

    foreach ($sections as $section=>$items)
    {
        foreach ($items as $item)
        {
            init_display($section . "_" . $item);
        }
    }
?>
}

//-->
</script>
</head>


<body onload="init()">

<table><tr>
  <!-- Option Selection -->
  <td>
    <form name="graph_selection" method="post" action=".">
    <table width=100%>
<?php
    foreach ($sections as $section=>$items)
    {
        echo "    <tr><td colspan=2><b>" . $section . "</b></td></tr>\n";
        foreach ($items as $item)
        {
            echo "      <tr><td>" . $item . "</td><td>\n";
            if ($section != "variables")
            {
                echo "       <select name=\"" . $section . "_" . $item . "\" align=\"right\" onchange='check_exact(this,\"" . $section . "_" . $item . "_exact\")'>\n";
                echo "       <option value=\"False\"" . select_if("False",$_POST[$section . "_" . $item]) . ">Ignore</option>\n";
                echo "       <option value=\"None\"" . select_if("None",$_POST[$section . "_" . $item]) . ">By Value</option>\n";
                echo "       <option value=\"Exact\"" . select_if("Exact",$_POST[$section . "_" . $item]) . ">Exact (Text)</option>\n";
                echo "       <option value=\"True\"" . select_if("True",$_POST[$section . "_" . $item]) . ">Ind. Variable</option>\n";
                echo "       </select></td></tr><tr><td colspan=2>\n";
            }
            else
            {
                echo "       <select name=\"" . $section . "_" . $item . "\" style=\"display:none\" align=\"right\" onchange='check_exact(this,\"" . $section . "_" . $item . "_exact\")'>\n";
                echo "       <option value=\"Exact\" selected>Exact (Text)</option>\n";
                echo "       </select></td></tr><tr><td colspan=2>\n";
            }
            echo "       <input name=\"" . $section . "_" . $item ."_exact\" type=\"text\" value=\"" . nab_exact($section . "_" . $item) . "\" size=\"30\" maxlength=\"30\"></td></tr>\n";
        }
    }
?>
    <tr><td colspan=2><br></td></tr>
    <tr><td colspan=2 align=center><input name="update" type="submit" value="Graph Result"></td></tr>
      </table>
    </form>
  </td>

  <!-- Image Panel -->
  <td>
    <img src="librarian.png" onclick="this.src='librarian.png?' + Math.random()">


  </td>
</tr></table>

</body>

</html>
