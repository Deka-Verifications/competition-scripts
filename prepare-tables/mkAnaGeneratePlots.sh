#!/bin/bash

source $(dirname "$0")/../configure.sh
#set -x

OUTPUTDIR="${RESULTSVERIFICATION}/";
#OUTPUTDIR="results-B/${RESULTSVERIFICATION}/";
QPLOTDIR="results-qplots/";

if [[ ${COMPETITIONNAME} == "SV-COMP" ]]; then
  SCALECOMMAND="set logscale y 10";
  XLABELCOMMAND="set xlabel 'Cumulative score'";
  YLABELCOMMAND="set ylabel 'Min. time in s' offset 3";
else
  SCALECOMMAND="unset logscale";
  XLABELCOMMAND="set xlabel 'Cumulative score'";
  YLABELCOMMAND="set ylabel 'Min. number of test tasks' offset 1";
fi

FORMATEXT="svg";  # 'pdf' or 'svg' or 'png'
if [[ $1 != "" ]]; then
    FORMATEXT=$1;
fi

if [[ "$FORMATEXT" = "pdf" ]]; then
  FORMAT="pdfcairo font \",16\" size 20cm,10cm";
  LINEWIDTH="2";
  TMARGIN="0.5";
  LMARGIN="9";
  RMARGIN="1.5";
  SIZEA="1,0.80";
  ORIGINA="0,0.18";
  SIZEB="1,0.18";
  ORIGINB="0,0";
  POINTINTERVAL=500;
elif [[ "$FORMATEXT" = "png" ]]; then
  FORMAT="pngcairo font \",8\" size 20cm,10cm";
  LINEWIDTH="1";
  TMARGIN="0.5";
  LMARGIN="7";
  RMARGIN="0.5";
  SIZEA="1,0.80";
  ORIGINA="0,0.2";
  SIZEB="1,0.2";
  ORIGINB="0,0";
  POINTINTERVAL=100;
else
  FORMAT="svg font \"Helvetica,8\" size 800,400";
  LINEWIDTH="2";
  TMARGIN="1.2";
  LMARGIN="7";
  RMARGIN="2.3";
  SIZEA="1,0.86";
  ORIGINA="0,0.150";
  SIZEB="1,0.14";
  ORIGINB="0,0.01";
  POINTINTERVAL=100;
fi

COLORS=(green red blue black navy magenta dark-cyan brown dark-violet sea-green);
#TOOLS=(Blast CPAchecker-Explicit CPAchecker-SeqCom CSeq ESBMC LLBMC Predator Symbiotic Threader UFO Ultimate);

for CAT in `ls ${QPLOTDIR}QPLOT.*.quantile-plot.csv | cut -d '.' -f 2 | sort -u`; do
    echo "
set terminal $FORMAT
set output 'quantilePlot-$CAT.$FORMATEXT'
set tmargin $TMARGIN
set bmargin 0
set lmargin $LMARGIN
set rmargin $RMARGIN
unset xlabel
unset xtics
$YLABELCOMMAND
#set key at -40, 500
set key top left
$SCALECOMMAND
set pointsize 1.0
set multiplot layout 2,1
set size $SIZEA
set origin $ORIGINA
" > quantilePlotShow.gp;
    echo $CAT;
    CMD="plot ";
    XRANGE=0;
    XMAX=0
    XMIN=0
    YMAX=0
    YMIN=0
    for TOOLFILE in `ls ${QPLOTDIR}QPLOT.$CAT.*.quantile-plot.csv`; do
      TOOL=`echo $TOOLFILE | cut -d '.' -f 3`;
      set +e
      TOOLSHORT=$(echo $TOOL | sed -e "s/ESBMC+DepthK/DepthK/" -e "s/SMACK+Corral/SMACK/" \
	                           -e "s/CoVeriTeam-Verifier-AlgoSelection/CVT-AlgoSel/" \
			           -e "s/CoVeriTeam-Verifier-ParallelPortfolio/CVT-ParPort/")
      XMINNEW=`cat "$TOOLFILE" | head -1 | cut -f 1 | sed "s/\..*//"`
      XMAXNEW=`cat "$TOOLFILE" | tail -1 | cut -f 1 | sed "s/\..*//"`
      set -e
      if [[ $XMAXNEW -ge $XMAX ]]; then
          XMAX=$XMAXNEW
      fi
      if [[ $XMINNEW -le $XMIN ]]; then
          XMIN=$XMINNEW
      fi
      set +e
      YMINNEW=`cat "$TOOLFILE" | head -1 | cut -f 2 | sed "s/\..*//"`
      YMAXNEW=`cat "$TOOLFILE" | tail -1 | cut -f 2 | sed "s/\..*//"`
      set -e
      if [[ $YMAXNEW -ge $YMAX ]]; then
          YMAX=$YMAXNEW
      fi
      if [[ $YMINNEW -le $YMIN ]]; then
          YMIN=$YMINNEW
      fi
      LINECOLOR=`grep "^$TOOL:" $(dirname "$0")/qPlotMapColor.cfg | cut -d : -f 2`;
      POINTTYPE=`grep "^$TOOL:" $(dirname "$0")/qPlotMapPointType.cfg | cut -d : -f 2`;
      #echo $TOOL $LINECOLOR $POINTTYPE
      CMD="$CMD '$TOOLFILE' using 1:2 with linespoints linecolor rgb \"${LINECOLOR}\" pointtype ${POINTTYPE} pointinterval $POINTINTERVAL linewidth ${LINEWIDTH} title '$TOOLSHORT',";
    done; # FOR tool
    if [[ $XMIN -lt $((-($XMAX/2))) ]]; then
        XMIN=$((-($XMAX/2)))
    fi
    if [[ $XMIN -gt $((-($XMAX/4))) ]]; then
        XMIN=$((-($XMAX/4)))
    fi
    XMAXROUNDINGBOX=100;
    XMINROUNDINGBOX=100;
    XRANGE=$(($XMAX - $XMIN))
    if [[ $XRANGE -lt 500 ]]; then
        XMAXROUNDINGBOX=10;
        XMINROUNDINGBOX=50;
    fi
    XMAX=$((($XMAX/$XMAXROUNDINGBOX + 1) * $XMAXROUNDINGBOX));
    XMIN=$((($XMIN/$XMINROUNDINGBOX - 1) * $XMINROUNDINGBOX));
    YMAXROUNDINGBOX=100;
    YRANGE=$(($YMAX - $YMIN))
    if [[ $YRANGE -lt 500 ]]; then
        YMAXROUNDINGBOX=10;
    fi
    YMAX=$((($YMAX/$YMAXROUNDINGBOX + 1) * $YMAXROUNDINGBOX));
    if [[ ${COMPETITIONNAME} == "SV-COMP" ]]; then
      echo "set xrange [$XMIN:$XMAX]" >> quantilePlotShow.gp;
      echo "set yrange [1:1000]" >> quantilePlotShow.gp;
    else
      echo "set xrange [0:$XMAX]" >> quantilePlotShow.gp;
      echo "set yrange [0:$YMAX]" >> quantilePlotShow.gp;
      echo "$XLABELCOMMAND" >> quantilePlotShow.gp;
      echo "set xtics nomirror" >> quantilePlotShow.gp;
    fi
    echo "$CMD%" | sed "s/,%/;/" >> quantilePlotShow.gp;
    if [[ ${COMPETITIONNAME} == "SV-COMP" ]]; then
      # Plot range from 0 to 1
      echo "
unset logscale
set yrange [0:1]
unset key
unset bmargin
set tmargin 0
set xtics nomirror
unset ytics
unset ylabel
set size $SIZEB
set origin $ORIGINB
$XLABELCOMMAND
" >> quantilePlotShow.gp;
      echo "$CMD%" | sed "s/,%/;/" >> quantilePlotShow.gp;
    fi

    gnuplot quantilePlotShow.gp;
done
/bin/mv quantilePlot* ${OUTPUTDIR};
