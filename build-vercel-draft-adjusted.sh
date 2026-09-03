#!/bin/sh
set -eu

# Preserve the known-good workbook-backed production build, then layer only the
# frozen, audited Draft-Adjusted PPG artifact and the stable final presentation layer.
sh build-vercel.sh

cp draft-adjusted-ppg.js draft-adjusted-ui.js final-ui-stable.js legacy-axis-fix.js workbook-ownership-fixes.js dist/

node <<'NODE'
const fs=require('fs');

const logoPath='M 495 425 L 466 451 L 426 481 L 432 490 L 432 599 L 427 609 L 445 617 L 463 628 L 483 645 L 520 610 L 546 582 L 545 580 L 521 598 L 504 605 L 489 597 L 470 581 L 471 546 L 516 506 L 545 485 L 514 450 Z M 474 457 L 475 458 L 475 460 L 477 462 L 477 463 L 483 470 L 483 471 L 485 473 L 485 474 L 489 478 L 489 479 L 491 481 L 491 482 L 494 485 L 494 486 L 496 488 L 496 489 L 498 491 L 498 492 L 500 494 L 500 495 L 504 500 L 504 501 L 505 502 L 505 504 L 496 513 L 495 513 L 485 523 L 484 523 L 479 528 L 478 528 L 472 534 L 471 534 L 470 533 L 470 461 Z M 847 426 L 829 440 L 814 442 L 797 437 L 779 421 L 756 443 L 714 472 L 718 479 L 719 524 L 716 534 L 737 546 L 750 557 L 711 624 L 705 640 L 704 652 L 711 639 L 719 631 L 731 626 L 746 626 L 759 631 L 781 652 L 789 640 L 810 620 L 829 607 L 842 602 L 837 592 L 837 545 L 841 532 L 818 514 L 803 499 L 799 491 L 774 523 L 763 515 L 756 507 L 756 460 L 761 453 L 770 464 L 784 471 L 805 472 L 820 465 L 834 451 Z M 799 550 L 799 605 L 795 609 L 788 603 L 787 603 L 782 599 L 781 599 L 774 595 L 772 595 L 771 594 L 769 594 L 768 593 L 764 593 L 763 592 L 752 592 L 751 593 L 747 593 L 746 594 L 741 595 L 734 599 L 733 599 L 732 598 L 734 596 L 734 595 L 736 593 L 736 592 L 738 590 L 738 589 L 740 587 L 740 586 L 742 584 L 742 583 L 744 581 L 744 580 L 746 578 L 746 577 L 748 575 L 748 574 L 750 572 L 750 571 L 752 569 L 752 568 L 754 566 L 754 565 L 756 563 L 756 562 L 758 560 L 758 559 L 760 557 L 760 556 L 762 554 L 762 553 L 764 551 L 764 550 L 766 548 L 766 547 L 768 545 L 768 544 L 770 542 L 770 541 L 772 539 L 772 538 L 774 536 L 774 535 L 777 532 L 778 533 L 779 533 L 785 539 L 786 539 L 791 544 L 792 544 L 797 549 L 798 549 Z M 390 359 L 364 379 L 337 393 L 348 403 L 351 410 L 351 594 L 349 601 L 340 611 L 354 619 L 379 644 L 415 604 L 400 604 L 393 597 L 389 585 Z M 628 357 L 613 361 L 557 390 L 565 397 L 568 404 L 568 595 L 565 603 L 558 611 L 571 614 L 589 623 L 610 637 L 623 650 L 640 632 L 660 616 L 681 604 L 695 600 L 689 589 L 689 480 L 696 466 L 677 452 L 653 428 L 608 462 L 609 389 L 615 371 Z M 626 462 L 650 483 L 650 604 L 644 610 L 633 603 L 617 591 L 608 583 L 608 477 Z M 174 354 L 144 388 L 87 432 L 138 420 L 152 428 L 159 444 L 159 472 L 110 516 L 132 509 L 142 511 L 155 523 L 159 537 L 157 662 L 149 699 L 135 730 L 178 694 L 213 674 L 200 655 L 201 428 L 213 409 L 267 457 L 267 583 L 258 594 L 217 560 L 216 621 L 229 628 L 239 642 L 277 597 L 318 574 L 311 558 L 311 457 L 319 434 L 276 407 L 240 372 L 223 384 L 205 384 L 191 376 Z M 929 116 L 890 142 L 900 154 L 900 267 L 890 276 L 878 268 L 867 253 L 867 115 L 848 130 L 825 142 L 836 154 L 836 274 L 833 281 L 869 309 L 900 280 L 901 310 L 909 332 L 896 345 L 869 327 L 845 327 L 822 344 L 811 367 L 829 354 L 842 353 L 864 361 L 883 378 L 903 354 L 941 319 L 933 310 L 929 296 Z M 402 112 L 367 140 L 373 142 L 381 154 L 381 279 L 374 292 L 383 297 L 399 314 L 423 291 L 413 279 L 413 158 L 432 143 L 449 162 L 448 284 L 444 292 L 450 295 L 466 312 L 471 304 L 491 287 L 481 279 L 479 273 L 479 164 L 486 150 L 456 112 L 414 146 L 411 128 Z M 342 112 L 302 140 L 314 152 L 313 266 L 300 276 L 276 256 L 276 111 L 232 140 L 244 152 L 244 271 L 240 280 L 281 308 L 312 279 L 314 306 L 327 332 L 314 346 L 286 325 L 272 321 L 258 322 L 238 333 L 224 355 L 241 344 L 259 345 L 282 358 L 301 378 L 325 349 L 357 319 L 349 306 L 345 288 L 346 132 Z M 563 108 L 527 142 L 519 156 L 519 171 L 524 182 L 533 189 L 544 193 L 526 204 L 506 221 L 505 283 L 513 289 L 531 307 L 534 312 L 540 304 L 566 279 L 567 283 L 581 297 L 591 310 L 593 310 L 600 299 L 620 278 L 609 278 L 602 271 L 600 266 L 600 153 L 607 141 L 586 128 Z M 554 194 L 556 196 L 557 196 L 558 197 L 560 197 L 565 200 L 567 200 L 569 202 L 568 203 L 568 209 L 569 210 L 569 234 L 568 235 L 568 241 L 569 242 L 569 252 L 568 253 L 568 265 L 569 266 L 565 270 L 564 270 L 561 273 L 560 273 L 558 275 L 557 275 L 554 278 L 553 277 L 552 277 L 548 273 L 547 273 L 537 263 L 537 262 L 536 261 L 536 220 L 537 219 L 537 216 L 538 215 L 538 213 L 540 211 L 540 210 L 542 208 L 542 207 L 545 204 L 545 203 L 548 200 L 549 200 L 553 196 L 553 195 Z M 544 136 L 545 137 L 545 138 L 546 139 L 546 140 L 554 148 L 555 148 L 558 151 L 559 151 L 561 153 L 562 153 L 565 156 L 566 156 L 569 159 L 569 191 L 568 192 L 566 192 L 565 191 L 562 191 L 561 190 L 558 190 L 557 189 L 554 189 L 551 187 L 549 187 L 548 186 L 546 186 L 545 185 L 544 185 L 543 184 L 542 184 L 541 183 L 540 183 L 539 182 L 538 182 L 537 181 L 536 181 L 530 175 L 530 174 L 529 173 L 529 172 L 527 169 L 527 166 L 526 165 L 526 161 L 527 160 L 527 157 L 528 156 L 528 153 L 529 152 L 529 151 L 532 148 L 532 147 L 535 144 L 536 144 Z M 733 116 L 721 123 L 707 123 L 694 117 L 682 105 L 657 131 L 629 153 L 629 210 L 657 232 L 628 287 L 620 309 L 634 296 L 643 293 L 656 293 L 674 301 L 687 314 L 707 291 L 732 274 L 731 217 L 733 211 L 701 180 L 697 171 L 677 201 L 668 195 L 660 186 L 660 143 L 665 138 L 680 149 L 686 151 L 701 150 L 709 146 L 719 137 Z M 678 211 L 679 211 L 685 217 L 686 217 L 692 223 L 693 223 L 700 230 L 700 272 L 701 273 L 700 274 L 699 277 L 698 278 L 687 269 L 686 269 L 679 265 L 677 265 L 676 264 L 672 264 L 671 263 L 664 263 L 663 264 L 659 264 L 658 265 L 653 266 L 652 267 L 647 269 L 644 272 L 643 272 L 642 271 L 643 270 L 643 269 L 647 264 L 647 263 L 648 262 L 650 257 L 652 255 L 654 250 L 658 245 L 658 244 L 659 243 L 659 242 L 661 240 L 663 235 L 667 230 L 668 227 L 670 225 L 671 222 L 673 220 L 675 215 L 677 213 L 677 212 Z M 791 60 L 755 114 L 734 140 L 757 142 L 757 276 L 752 285 L 769 297 L 782 312 L 815 277 L 814 275 L 808 279 L 802 279 L 791 269 L 788 261 L 788 142 L 809 141 L 825 121 L 788 119 L 788 85 Z M 117 0 L 98 31 L 74 54 L 35 76 L 1 85 L 20 92 L 37 106 L 47 125 L 49 144 L 46 191 L 35 205 L 17 214 L 31 219 L 42 229 L 48 246 L 46 271 L 32 304 L 0 341 L 34 328 L 72 328 L 97 340 L 106 349 L 112 361 L 171 302 L 201 281 L 217 275 L 208 259 L 208 120 L 217 100 L 185 80 L 156 56 L 130 26 Z M 101 68 L 109 68 L 117 72 L 140 88 L 160 110 L 166 122 L 168 131 L 168 273 L 156 293 L 142 309 L 121 301 L 105 297 L 91 296 L 73 298 L 55 305 L 52 304 L 77 282 L 93 261 L 93 71 Z';
const goldDefs=`<defs>
  <linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ffe49a"/>
    <stop offset="0.34" stop-color="#efbd49"/>
    <stop offset="0.66" stop-color="#d99b25"/>
    <stop offset="1" stop-color="#b77915"/>
  </linearGradient>
</defs>`;

const appSvg=`<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512" role="img" aria-label="Dynasty Plebs">
${goldDefs}
<rect width="512" height="512" fill="#090807"/>
<g transform="translate(58.39 102.70) scale(.42)">
  <path d="${logoPath}" fill="url(#gold)" fill-rule="evenodd" stroke="#ffe8ad" stroke-width="1.7" stroke-linejoin="round"/>
</g>
</svg>`;
const siteSvg=`<svg xmlns="http://www.w3.org/2000/svg" width="941" height="730" viewBox="0 0 941 730" role="img" aria-label="Dynasty Plebs">
${goldDefs}
<path d="${logoPath}" fill="url(#gold)" fill-rule="evenodd" stroke="#ffe8ad" stroke-width="1.5" stroke-linejoin="round"/>
</svg>`;
fs.writeFileSync('dist/plebs-icon.svg',appSvg);
fs.writeFileSync('dist/plebs-logo.svg',siteSvg);
fs.writeFileSync('dist/manifest.webmanifest',JSON.stringify({
  name:'Dynasty Plebs',
  short_name:'Plebs',
  start_url:'/',
  scope:'/',
  display:'standalone',
  background_color:'#17130e',
  theme_color:'#17130e',
  icons:[{src:'/plebs-icon.svg?v=5',sizes:'any',type:'image/svg+xml',purpose:'any'}]
},null,2));

const path='dist/index.html';
let html=fs.readFileSync(path,'utf8');
const needle='<script src="regression-fix.js?v=1"></script>';
if((html.match(new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'g'))||[]).length!==1){
  throw new Error('Expected exactly one regression-fix script tag');
}
const layered='<script src="draft-adjusted-ppg.js?v=2"></script>\n'+needle+'\n<script src="draft-adjusted-ui.js?v=2"></script>';
html=html.replace(needle,layered);
const ownershipNeedle='<script src="app-v2.js"></script>';
if(!html.includes(ownershipNeedle))throw new Error('Expected app-v2 script tag');
html=html.replace(ownershipNeedle,'<script src="workbook-ownership-fixes.js?v=1"></script>\n'+ownershipNeedle);

const brandNeedle='<a class="brand" href="#"><strong>Dynasty Plebs</strong><small>Est. 2019</small></a>';
const brandLogo='<a class="brand dp-brand-logo" href="#" aria-label="Dynasty Plebs"><img src="/plebs-logo.svg?v=5" alt="Dynasty Plebs"></a>';
if(!html.includes(brandNeedle))throw new Error('Expected Dynasty Plebs text brand');
html=html.replace(brandNeedle,brandLogo);

const headLayers=`
<link rel="manifest" href="/manifest.webmanifest?v=5">
<link rel="icon" type="image/svg+xml" href="/plebs-icon.svg?v=5">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Dynasty Plebs">
<style>
.dp-brand-logo{display:flex!important;align-items:center!important;min-width:132px!important;padding:0!important}
.dp-brand-logo img{display:block;width:128px;height:auto}
@media(min-width:681px){.dp-brand-logo{min-width:172px!important}.dp-brand-logo img{width:166px}}
</style>
`;
if(!html.includes('</head>'))throw new Error('Expected closing head tag');
html=html.replace('</head>',headLayers+'</head>');
const endLayers='<script src="final-ui-stable.js?v=2"></script>\n<script src="legacy-axis-fix.js?v=1"></script>\n';
if(!html.includes('</body>'))throw new Error('Expected closing body tag');
html=html.replace('</body>',endLayers+'</body>');
fs.writeFileSync(path,html);
NODE

node --check dist/draft-adjusted-ppg.js
node --check dist/draft-adjusted-ui.js
node --check dist/final-ui-stable.js
node --check dist/legacy-axis-fix.js
node --check dist/workbook-ownership-fixes.js
grep -Fq 'draft-adjusted-ppg.js?v=2' dist/index.html
grep -Fq 'draft-adjusted-ui.js?v=2' dist/index.html
grep -Fq 'workbook-ownership-fixes.js?v=1' dist/index.html
grep -Fq 'final-ui-stable.js?v=2' dist/index.html
grep -Fq 'legacy-axis-fix.js?v=1' dist/index.html
grep -Fq 'manifest.webmanifest?v=5' dist/index.html
grep -Fq 'plebs-icon.svg?v=5' dist/index.html
grep -Fq 'plebs-logo.svg?v=5' dist/index.html
grep -Fq 'dp-brand-logo' dist/index.html
grep -Fq 'draft-adjusted-ppg-v2' dist/draft-adjusted-ppg.js
grep -Fq 'Career PPG minus the expected Career PPG for a rookie at the same position and draft slot.' dist/draft-adjusted-ui.js
grep -Fq '#draftBoard .dp-compact-owner' dist/final-ui-stable.js
grep -Fq '#managerTimeline .dp-series' dist/final-ui-stable.js
grep -Fq 'Avg PF/Game' dist/final-ui-stable.js
grep -Fq 'Draft Class Average' dist/final-ui-stable.js
grep -Fq 'activeFirstSort' dist/final-ui-stable.js
grep -Fq 'dp-intel-card>b' dist/final-ui-stable.js
grep -Fq 'STEP=500' dist/legacy-axis-fix.js
grep -Fq "jefferson.owner='Seth Miller'" dist/workbook-ownership-fixes.js
